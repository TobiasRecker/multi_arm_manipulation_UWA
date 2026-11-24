// File-only diagnostic: never initializes ROS, opens a socket or commands a robot.
#include "uwa_cell_protection/collision_core.hpp"
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>

int main(int argc, char ** argv)
{
  using namespace uwa_cell_protection;
  if (argc != 3) { std::cerr << "Usage: collision_replay model-config.json states.json\n"; return 2; }
  try {
    const auto before = std::chrono::steady_clock::now();
    const auto config = load_config(argv[1]);
    CollisionCore core(config, std::filesystem::path(argv[1]).parent_path().string());
    const double load = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - before).count();
    std::ifstream source(argv[2]);
    if (!source) throw std::runtime_error("Cannot read saved replay states");
    const auto input = Json::parse(source);
    const auto & states = input.is_array() ? input : input.at("states");
    std::set<std::string> available;
    if (input.is_object() && input.contains("available_arms"))
      available = input.at("available_arms").get<std::set<std::string>>();
    else for (const auto * arm : arm_ids) available.insert(arm);
    Json output{{"model_signature", config.at("model_signature")}, {"load_ms", load}, {"states", Json::array()}};
    for (const auto & positions : states) {
      const auto start = std::chrono::steady_clock::now();
      auto decision = core.evaluate(positions.get<std::map<std::string, double>>(), available);
      decision["duration_ms"] = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
      output["states"].push_back(decision);
    }
    std::cout << output.dump() << '\n'; return 0;
  } catch (const std::exception & error) { std::cerr << error.what() << '\n'; return 1; }
}
