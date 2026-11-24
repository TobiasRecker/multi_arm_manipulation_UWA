#include <cassert>
#include <cmath>
#include <iostream>
#include "uwa_cell_protection/pause_ramp.hpp"

int main()
{
  using uwa_cell_protection::next_pause_factor;
  for (double dt : {0.002, 0.008, 0.01}) {
    for (double velocity : {-0.1, -0.03, 0.0, 0.03, 0.1}) {
      for (double acceleration : {-0.2, -0.1, 0.0, 0.1, 0.2}) {
        for (bool paused : {false, true}) {
          for (double factor : {0.0, 0.1, 0.5, 0.9, 1.0}) {
            const double next = next_pause_factor(factor, paused, dt, 0.2, 0.1,
              {velocity}, {acceleration});
            assert(next >= 0.0 && next <= 1.0);
            assert(paused ? next <= factor : next >= factor);
            const double rate = (next - factor) / dt;
            for (double r : {factor, next}) {
              assert(std::abs(r * r * acceleration + rate * velocity) <= 0.2 + 1e-9);
            }
          }
        }
      }
    }
  }
  double factor = 1.0;
  for (int i = 0; i < 50; ++i) {
    factor = next_pause_factor(factor, true, 0.01, 0.2, 0.1, {0.1}, {0.0});
  }
  assert(factor < 1e-12);
  assert(next_pause_factor(0.0, true, 0.01, 0.2, 0.1, {0.1}, {0.0}) == 0.0);
  assert(next_pause_factor(1.0, false, 0.01, 0.2, 0.1, {0.1}, {0.0}) == 1.0);
  std::cout << "pause ramp chain-rule bounds passed\n";
}
