#include "uwa_cell_protection/collision_core.hpp"
#include <cmath>
#include <filesystem>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <moveit/planning_scene/planning_scene.hpp>
#include <moveit/robot_model/robot_model.hpp>
#include <moveit/robot_state/robot_state.hpp>
#include <moveit_msgs/msg/collision_object.hpp>
#include <shape_msgs/msg/plane.hpp>
#include <srdfdom/model.h>
#include <urdf_parser/urdf_parser.h>

namespace uwa_cell_protection
{
namespace
{
std::string read(const std::filesystem::path & path)
{
  std::ifstream stream(path);
  if (!stream) throw std::runtime_error("Cannot read model: " + path.string());
  return {std::istreambuf_iterator<char>(stream), {}};
}
std::string arm_of(const std::string & link)
{
  const auto name = link.rfind("calibrated/", 0) == 0 ? link.substr(11) : link;
  for (const auto * arm : arm_ids)
    if (name.rfind(std::string(arm) + "_", 0) == 0) return arm;
  return "";
}
}
Json load_config(const std::string & path)
{
  const auto config = Json::parse(read(path));
  if (config.value("schema_version", 0) != 1)
    throw std::runtime_error("Unsupported protection model schema");
  return config;
}
struct CollisionCore::Impl
{
  struct Sphere { std::string link; Eigen::Vector3d centre; double radius; };
  moveit::core::RobotModelPtr model;
  std::unique_ptr<planning_scene::PlanningScene> scene;
  std::unique_ptr<moveit::core::RobotState> state;
  std::map<std::string, std::vector<Sphere>> spheres;
  std::map<unsigned, collision_detection::AllowedCollisionMatrix> matrices;
  std::map<std::string, std::vector<std::string>> names;
  double margin;

  Impl(const Json & config, const std::string & directory)
    : margin(config.value("neighbor_margin_m", .04))
  {
    if (!std::isfinite(margin) || margin != .04)
      throw std::runtime_error("This approved protection profile requires 0.04 m neighbor margin");
    const auto path = [&](const char * field) {
      auto p = std::filesystem::path(config.at(field).get<std::string>());
      return p.is_absolute() ? p : std::filesystem::path(directory) / p;
    };
    auto urdf = urdf::parseURDF(read(path("urdf_path")));
    if (!urdf) throw std::runtime_error("Invalid URDF");
    auto srdf = std::make_shared<srdf::Model>();
    if (!srdf->initString(*urdf, read(path("srdf_path"))))
      throw std::runtime_error("Invalid SRDF");
    model = std::make_shared<moveit::core::RobotModel>(urdf, srdf);
    scene = std::make_unique<planning_scene::PlanningScene>(model);
    state = std::make_unique<moveit::core::RobotState>(model);
    state->setToDefaultValues();
    moveit_msgs::msg::CollisionObject floor;
    floor.header.frame_id = "world";
    floor.id = "calibration_floor";
    shape_msgs::msg::Plane plane;
    plane.coef = {0., 0., 1., .003};
    geometry_msgs::msg::Pose pose;
    pose.orientation.w = 1.;
    floor.planes.push_back(plane);
    floor.plane_poses.push_back(pose);
    floor.operation = moveit_msgs::msg::CollisionObject::ADD;
    scene->processCollisionObjectMsg(floor);
    for (const auto * link : model->getLinkModels()) {
      bool fixed = true;
      for (auto * p = link; p && p->getParentJointModel(); p = p->getParentLinkModel())
        if (p->getParentJointModel()->getType() != moveit::core::JointModel::FIXED) {
          fixed = false;
          break;
        }
      if (fixed) scene->getAllowedCollisionMatrixNonConst().setEntry(link->getName(), floor.id, true);
    }
    for (const auto * arm : arm_ids) {
      names[arm] = config.at("arms").at(arm).at("joint_names").get<std::vector<std::string>>();
      if (names[arm].size() != 6) throw std::runtime_error("Expected six arm joints");
      for (const auto & joint : names[arm])
        if (std::find(model->getVariableNames().begin(), model->getVariableNames().end(), joint) == model->getVariableNames().end())
          throw std::runtime_error("Model joint missing: " + joint);
      for (const auto & sphere : config.at("spheres").at(arm)) {
        const auto c = sphere.at("centre").get<std::array<double, 3>>();
        Sphere item{sphere.at("link"), Eigen::Vector3d(c[0], c[1], c[2]), sphere.at("radius")};
        if (!model->getLinkModel(item.link) || !item.centre.allFinite() ||
            !std::isfinite(item.radius) || item.radius <= 0.)
          throw std::runtime_error("Invalid collision sphere");
        spheres[arm].push_back(item);
      }
      if (spheres[arm].empty()) throw std::runtime_error("Missing arm sphere bodies");
    }
    // Cache all sixteen availability masks. Unknown arms are omitted, never
    // silently placed at a default or last-known pose in a reported decision.
    for (unsigned mask = 0; mask != 16; ++mask) {
      auto matrix = scene->getAllowedCollisionMatrix();
      for (unsigned i = 0; i < arm_ids.size(); ++i) {
        if (mask & (1u << i)) continue;
        for (const auto * link : model->getLinkModels()) {
          if (arm_of(link->getName()) != arm_ids[i]) continue;
          matrix.setEntry(link->getName(), true);
          matrix.setEntry(link->getName(), floor.id, true);
        }
      }
      matrices.emplace(mask, std::move(matrix));
    }
  }
};
CollisionCore::CollisionCore(const Json & config, const std::string & directory)
  : impl_(std::make_unique<Impl>(config, directory)) {}
CollisionCore::~CollisionCore() = default;
Json CollisionCore::evaluate(const std::map<std::string, double> & positions,
                             const std::set<std::string> & available)
{
  auto & p = *impl_;
  unsigned mask = 0;
  for (unsigned i = 0; i < arm_ids.size(); ++i) {
    if (!available.count(arm_ids[i])) continue;
    mask |= 1u << i;
    for (const auto & joint : p.names.at(arm_ids[i])) {
      auto it = positions.find(joint);
      if (it == positions.end() || !std::isfinite(it->second))
        throw std::runtime_error("Incomplete finite collision state: " + joint);
      p.state->setVariablePosition(joint, it->second);
    }
  }
  p.state->update();
  Json conflicts = Json::array(), pairs = Json::array();
  if (mask) {
    collision_detection::CollisionRequest request;
    collision_detection::CollisionResult result;
    request.contacts = true;
    request.max_contacts = 100;
    request.max_contacts_per_pair = 1;
    // Deliberately no satisfiesBounds() call: this is geometry, not another
    // joint-limit monitor hidden behind the collision interface.
    p.scene->checkCollision(request, result, *p.state, p.matrices.at(mask));
    for (const auto & contact : result.contacts)
      conflicts.push_back({{"kind", "fcl_contact"},
                           {"links", {contact.first.first, contact.first.second}},
                           {"distance_m", 0.}, {"threshold_m", 0.}});
    if (result.collision && result.contacts.empty())
      conflicts.push_back({{"kind", "fcl_contact"}, {"links", Json::array()},
                           {"distance_m", 0.}, {"threshold_m", 0.}});
  }
  std::map<std::string, std::vector<Eigen::Vector3d>> world;
  for (const auto & arm : available)
    for (const auto & s : p.spheres.at(arm))
      world[arm].push_back(p.state->getGlobalLinkTransform(s.link) * s.centre);
  for (const auto & pair : neighbor_pairs) {
    if (!available.count(pair[0]) || !available.count(pair[1])) continue;
    double minimum = std::numeric_limits<double>::infinity();
    size_t ai = 0, bi = 0;
    const auto & a = p.spheres.at(pair[0]);
    const auto & b = p.spheres.at(pair[1]);
    for (size_t i = 0; i < a.size(); ++i)
      for (size_t j = 0; j < b.size(); ++j) {
        double gap = (world.at(pair[0])[i] - world.at(pair[1])[j]).norm() - a[i].radius - b[j].radius;
        if (gap < minimum) { minimum = gap; ai = i; bi = j; }
      }
    Json entry{{"kind", "neighbor_margin"}, {"arms", {pair[0], pair[1]}},
               {"links", {a[ai].link, b[bi].link}},
               {"distance_m", minimum}, {"threshold_m", p.margin}};
    pairs.push_back(entry);
    if (minimum <= p.margin) conflicts.push_back(entry);
  }
  return {{"collisions", conflicts}, {"pairs", pairs}, {"clear", conflicts.empty()}};
}
}  // namespace uwa_cell_protection
