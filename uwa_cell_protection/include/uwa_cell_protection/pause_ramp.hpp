#pragma once

#include <algorithm>
#include <cmath>
#include <vector>

namespace uwa_cell_protection
{
// The pause factor changes virtual time, not the approved normal trajectory.
// Bound the added acceleration using |r^2 q'' + r' q'| <= acceleration.
// The magnitude bound deliberately also covers changes of derivative sign.
inline double next_pause_factor(
  double factor, bool paused, double dt, double acceleration, double normal_velocity,
  const std::vector<double> & velocity, const std::vector<double> & path_acceleration)
{
  if (!(dt > 0.0)) {return factor;}
  const double target = paused ? 0.0 : 1.0;
  const double direction = paused ? -1.0 : 1.0;
  const double maximum = std::min(std::abs(target - factor), acceleration / normal_velocity * dt);
  auto admissible = [&](double change) {
      const double next = factor + direction * change;
      const double largest_factor = std::max(factor, next);
      for (size_t i = 0; i < velocity.size(); ++i) {
        const double a = i < path_acceleration.size() ? std::abs(path_acceleration[i]) : 0.0;
        if (largest_factor * largest_factor * a + change / dt * std::abs(velocity[i]) >
          acceleration + 1e-12) {return false;}
      }
      return true;
    };
  double change = maximum;
  if (!admissible(change)) {
    double low = 0.0, high = change;
    for (int i = 0; i < 48; ++i) {
      const double middle = (low + high) * 0.5;
      if (admissible(middle)) {low = middle;} else {high = middle;}
    }
    change = low;
  }
  return std::clamp(factor + direction * change, 0.0, 1.0);
}
}  // namespace uwa_cell_protection
