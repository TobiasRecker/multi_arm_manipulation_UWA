// Command-free process: native OMPL RRTConnect with full-cell MoveIt/FCL checks.
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <nlohmann/json.hpp>
#include <urdf_parser/urdf_parser.h>
#include <srdfdom/model.h>
#include <moveit/robot_model/robot_model.hpp>
#include <moveit/robot_state/robot_state.hpp>
#include <moveit/planning_scene/planning_scene.hpp>
#include <moveit_msgs/msg/collision_object.hpp>
#include <ompl/base/spaces/RealVectorStateSpace.h>
#include <ompl/geometric/SimpleSetup.h>
#include <ompl/geometric/planners/rrt/RRTConnect.h>
#include <ompl/util/RandomNumbers.h>

using json = nlohmann::json;
std::string read(const std::string &path) { std::ifstream f(path); if (!f) throw std::runtime_error("Cannot read "+path); return {std::istreambuf_iterator<char>(f), {}}; }

int main(int argc, char **argv)
{
  if (argc!=3) return 2;
  json output;
  try {
    const auto request = json::parse(read(argv[1]));
    auto urdf = urdf::parseURDF(read(request.at("urdf")));
    if (!urdf) throw std::runtime_error("Invalid URDF");
    auto srdf = std::make_shared<srdf::Model>();
    if (!srdf->initString(*urdf, read(request.at("srdf")))) throw std::runtime_error("Invalid SRDF");
    auto robot = std::make_shared<moveit::core::RobotModel>(urdf, srdf);
    planning_scene::PlanningScene scene(robot);
    moveit_msgs::msg::CollisionObject floor;
    floor.header.frame_id="world"; floor.id="calibration_floor";
    shape_msgs::msg::Plane plane; plane.coef={0.,0.,1.,.003};
    geometry_msgs::msg::Pose pose; pose.orientation.w=1.;
    floor.planes.push_back(plane); floor.plane_poses.push_back(pose);
    floor.operation=moveit_msgs::msg::CollisionObject::ADD;
    scene.processCollisionObjectMsg(floor);
    for (const auto *link : robot->getLinkModels()) {
      bool fixed=true;
      for (auto *p=link; p && p->getParentJointModel(); p=p->getParentLinkModel())
        if (p->getParentJointModel()->getType()!=moveit::core::JointModel::FIXED) { fixed=false; break; }
      if (fixed) scene.getAllowedCollisionMatrixNonConst().setEntry(link->getName(), "calibration_floor", true);
    }
    moveit::core::RobotState state(robot); state.setToDefaultValues();
    std::map<std::string,double> initial=request.at("start").get<std::map<std::string,double>>();
    state.setVariablePositions(initial); state.update();
    struct Sphere { std::string link; Eigen::Vector3d centre; double radius; };
    std::map<std::string,std::vector<Sphere>> spheres;
    if (request.contains("spheres")) for (auto arm=request["spheres"].begin(); arm!=request["spheres"].end(); ++arm)
      for (const auto &s : arm.value()) spheres[arm.key()].push_back(
        {s["link"], Eigen::Vector3d(s["centre"][0],s["centre"][1],s["centre"][2]),s["radius"]});
    auto names=request.at("joint_names").get<std::vector<std::string>>();
    auto space=std::make_shared<ompl::base::RealVectorStateSpace>(names.size());
    ompl::base::RealVectorBounds bounds(names.size());
    for (size_t i=0; i<names.size(); ++i) {
      const auto &b=robot->getVariableBounds(names[i]);
      bounds.setLow(i,b.min_position_); bounds.setHigh(i,b.max_position_);
    }
    space->setBounds(bounds);
    ompl::RNG::setSeed(request.value("seed", 1u)+1u);
    ompl::geometric::SimpleSetup ss(space);
    ss.setStateValidityChecker([&](const ompl::base::State *s) {
      auto *v=s->as<ompl::base::RealVectorStateSpace::StateType>();
      for (size_t i=0; i<names.size(); ++i) state.setVariablePosition(names[i],v->values[i]);
      state.update();
      // Match CollisionModel::check's 1e-8rad tolerance. Simulated gripper
      // drives at their zero limit can report tiny negative roundoff.
      if (!state.satisfiesBounds(1e-8) || scene.isStateColliding(state)) return false;
      std::map<std::string,std::vector<Eigen::Vector3d>> world;
      for (const auto &[arm, shapes] : spheres) for (const auto &s : shapes)
        world[arm].push_back(state.getGlobalLinkTransform(s.link)*s.centre);
      if (request.contains("pair_thresholds")) for (const auto &pair : request["pair_thresholds"]) {
        const std::string a=pair["arms"][0], b=pair["arms"][1];
        for (size_t i=0; i<spheres[a].size(); ++i) for (size_t j=0; j<spheres[b].size(); ++j) {
          const double limit=spheres[a][i].radius+spheres[b][j].radius+pair["threshold_m"].get<double>();
          if ((world[a][i]-world[b][j]).squaredNorm()<=limit*limit) return false;
        }
      }
      return true;
    });
    // Absolute Euclidean step <=5mrad implies each joint step <=5mrad.
    ss.getSpaceInformation()->setStateValidityCheckingResolution(
      std::min(0.01, request.value("check_step",.005)/space->getMaximumExtent()));
    ompl::base::ScopedState<> start(space), goal(space);
    auto target=request.at("target").get<std::vector<double>>();
    if (target.size()!=names.size()) throw std::runtime_error("Wrong target dimension");
    for (size_t i=0; i<names.size(); ++i) { start[i]=initial.at(names[i]); goal[i]=target[i]; }
    ss.setStartAndGoalStates(start, goal, 1e-8);
    auto planner=std::make_shared<ompl::geometric::RRTConnect>(ss.getSpaceInformation());
    planner->setRange(0.15);  // radians: default extent-scaled steps are too large in this cell
    ss.setPlanner(planner);
    const auto solved=ss.solve(request.value("budget_s",10.));
    if (solved!=ompl::base::PlannerStatus::EXACT_SOLUTION) {
      output={{"success",false},{"error","No exact RRTConnect solution within budget"}};
    } else {
      ss.simplifySolution(0.1);  // included in the caller's hard wall-clock budget
      auto &path=ss.getSolutionPath();
      json points=json::array();
      for (const auto *s : path.getStates()) {
        auto *v=s->as<ompl::base::RealVectorStateSpace::StateType>();
        points.push_back(std::vector<double>(v->values,v->values+names.size()));
      }
      output={{"success",true},{"path",points},{"algorithm","OMPL geometric::RRTConnect / MoveIt FCL"}};
    }
  } catch (const std::exception &e) { output={{"success",false},{"error",e.what()}}; }
  std::ofstream(argv[2]) << output.dump(2) << '\n';
  return output.value("success",false) ? 0 : 1;
}
