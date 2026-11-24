#pragma once
#include <array>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <vector>
#include <nlohmann/json.hpp>

namespace uwa_cell_protection
{
using Json = nlohmann::json;
inline constexpr std::array<const char *, 4> arm_ids{
  "left_front", "left_rear", "right_front", "right_rear"};
inline constexpr std::array<std::array<const char *, 2>, 4> neighbor_pairs{{
  {"left_front", "right_front"}, {"left_front", "left_rear"},
  {"right_front", "right_rear"}, {"left_rear", "right_rear"}}};

// Pure geometry only: no bounds, velocities, controller inventory or data-age policy.
class CollisionCore
{
public:
  explicit CollisionCore(const Json & config, const std::string & directory = ".");
  ~CollisionCore();
  CollisionCore(const CollisionCore &) = delete;
  CollisionCore & operator=(const CollisionCore &) = delete;
  Json evaluate(const std::map<std::string, double> & positions,
                const std::set<std::string> & available);
private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
Json load_config(const std::string & path);
}  // namespace uwa_cell_protection
