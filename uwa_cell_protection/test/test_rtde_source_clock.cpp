#include "uwa_cell_protection/rtde_source_clock.hpp"

#include <cassert>
#include <cmath>
#include <limits>

using uwa_cell_protection::RtdeSourceClock;

int main()
{
  // First frame is anchored on the start request, including start latency.
  RtdeSourceClock clock(100.);
  assert(!clock.observe(4., 99.));
  assert(!clock.observe(std::numeric_limits<double>::quiet_NaN(), 100.));
  assert(clock.observe(4., 100.02).value() == 100.);
  assert(!clock.observe(4., 100.04));
  assert(!clock.observe(3.99, 100.04));
  assert(!clock.observe(7.05, 100.07));
  const double after_outlier = clock.observe(4.05, 100.07).value();
  assert(std::abs(after_outlier - 100.05) < .001);

  // Delay that lasts much longer than the freshness window never becomes
  // fresh solely because subsequent packets are evenly spaced.
  for (int i = 2; i <= 1000; ++i) {
    const double sample = 4. + i * .05;
    const double received = 100.32 + i * .05;
    const double source = clock.observe(sample, received).value();
    assert(received - source > .30);
  }
  const double catchup = clock.observe(54.4, 150.42).value();
  assert(150.42 - catchup < .021);

  // A new negotiated stream uses its own epoch, even for a reset device.
  RtdeSourceClock next(200.);
  assert(next.observe(.01, 200.03).value() == 200.);
  assert(next.observe(.06, 200.08).value() <= 200.08);

  // Long-running healthy streams with bounded positive or negative drift.
  for (double rate : {.9994, 1.0006}) {
    RtdeSourceClock drifting(300.);
    for (int i = 0; i <= 144000; ++i) {
      const double received = 300.02 + i * .05;
      const double device = 2000. + i * .05 * rate;
      const double source = drifting.observe(device, received).value();
      assert(source <= received && received - source < .025);
    }
  }
}
