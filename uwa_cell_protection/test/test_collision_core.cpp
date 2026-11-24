#include "uwa_cell_protection/collision_core.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <unistd.h>

using namespace uwa_cell_protection;
void require(bool passed, const char * reason)
{
  if (!passed) throw std::runtime_error(reason);
}
int main()
{
  const auto directory = std::filesystem::temp_directory_path() /
    ("uwa-protection-core-" + std::to_string(::getpid()));
  std::filesystem::create_directory(directory);
  try {
    std::string urdf = "<robot name='cell'><link name='world'/><link name='table'><collision>"
      "<geometry><box size='0.2 0.2 0.2'/></geometry></collision></link>"
      "<joint name='table_mount' type='fixed'><parent link='world'/><child link='table'/>"
      "<origin xyz='1 0 1'/></joint>";
    Json config{{"neighbor_margin_m", .04}, {"urdf_path", "robot.urdf"}, {"srdf_path", "robot.srdf"}};
    std::map<std::string, double> positions;
    std::set<std::string> all;
    unsigned index = 0;
    for (const auto * rid : arm_ids) {
      const std::string arm(rid);
      all.insert(arm);
      std::vector<std::string> names;
      std::string parent = "world";
      for (unsigned j = 0; j != 6; ++j) {
        const auto joint = arm + "_joint" + std::to_string(j);
        const auto link = arm + "_link" + std::to_string(j);
        names.push_back(joint); positions[joint] = 0.;
        urdf += "<link name='" + link + "'>";
        if (j == 5) urdf += "<collision><geometry><sphere radius='0.1'/></geometry></collision>";
        urdf += "</link><joint name='" + joint + "' type='" + (j == 0 ? "prismatic" : "revolute") +
          "'><parent link='" + parent + "'/><child link='" + link + "'/>";
        if (j == 0) urdf += "<origin xyz='" + std::to_string(index * 3) + " 0 1'/>";
        urdf += "<axis xyz='1 0 0'/><limit lower='-0.1' upper='0.1' velocity='1' effort='1'/></joint>";
        parent = link;
      }
      config["arms"][arm]["joint_names"] = names;
      config["spheres"][arm] = Json::array({{{"link", parent}, {"centre", {0., 0., 0.}}, {"radius", .1}}});
      ++index;
    }
    urdf += "</robot>";
    std::ofstream(directory / "robot.urdf") << urdf;
    std::ofstream(directory / "robot.srdf") << "<robot name='cell'/>";
    CollisionCore core(config, directory.string());
    require(core.evaluate(positions, all).at("clear"), "Separated cell should be clear");
    // The live geometric core deliberately does not reintroduce joint bounds.
    positions["left_front_joint0"] = -.5;
    require(core.evaluate(positions, all).at("clear"), "Out-of-bounds clear geometry must remain clear");
    positions["left_front_joint0"] = 0.;
    positions["right_front_joint0"] = -5.77;
    auto margin = core.evaluate(positions, all);
    require(!margin.at("clear").get<bool>(), "Neighbor margin must trigger before FCL contact");
    require(margin.at("collisions").at(0).at("kind") == "neighbor_margin", "Wrong neighbor conflict reason");
    auto partial = all;
    partial.erase("right_front");
    require(core.evaluate(positions, partial).at("clear"), "Unavailable arm must be omitted, not checked at stale pose");
    positions["right_front_joint0"] = 0.;
    positions["right_rear_joint0"] = -8.77;
    require(core.evaluate(positions, all).at("clear"), "No invented 40mm margin on diagonal arm pair");
    positions["right_rear_joint0"] = -8.85;
    auto diagonal = core.evaluate(positions, all);
    require(!diagonal.at("clear").get<bool>(), "Full FCL must cover diagonal collision");
    require(diagonal.at("collisions").at(0).at("kind") == "fcl_contact", "Wrong diagonal conflict reason");
    positions["right_rear_joint0"] = 0.;
    positions["left_front_joint0"] = 1.;
    require(!core.evaluate(positions, all).at("clear").get<bool>(), "FCL must cover table collision");
    require(core.evaluate({}, {}).at("clear"), "No data produces no fabricated collision");
    std::filesystem::remove_all(directory);
    std::cout << "Collision core: clear, no joint limits, neighbor margin, missing data, diagonal and table cases passed\n";
    return 0;
  } catch (const std::exception & error) {
    std::filesystem::remove_all(directory);
    std::cerr << error.what() << '\n'; return 1;
  }
}
