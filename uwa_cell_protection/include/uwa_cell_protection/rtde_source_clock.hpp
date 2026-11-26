#pragma once

#include <algorithm>
#include <cmath>
#include <optional>

namespace uwa_cell_protection
{
class RtdeSourceClock
{
public:
  // Create a clock for each negotiated RTDE stream. The start request is a
  // lower bound for the capture time of its first packet.
  explicit RtdeSourceClock(double stream_start) : stream_start_(stream_start) {}

  std::optional<double> observe(double stamp, double received)
  {
    if (!std::isfinite(stamp) || !std::isfinite(received) || received < stream_start_) {
      return std::nullopt;
    }
    if (!initialized_) {
      initialized_ = true;
      stamp_ = stamp;
      received_ = received;
      offset_ = stream_start_ - stamp;
      return stream_start_;
    }

    const double device_step = stamp - stamp_;
    const double host_step = received - received_;
    const double observed_offset = received - stamp;
    const double residual = observed_offset - offset_;
    if (device_step <= 0. || host_step < 0. || residual < -tracking_window_) {
      return std::nullopt;
    }

    // Only adjust on uninterrupted, low-latency samples. A packet delayed
    // beyond that window cannot pull the source clock forward. The bound is
    // one millisecond of correction per second of real stream progression.
    if (device_step <= tracking_window_ * 2. && host_step <= tracking_window_ * 2. &&
        residual <= tracking_window_) {
      const double budget = std::min(device_step, host_step) * max_drift_;
      offset_ += std::clamp(residual, -budget, budget);
    }
    stamp_ = stamp;
    received_ = received;
    return std::min(stamp + offset_, received);
  }

private:
  static constexpr double tracking_window_ = .05;
  static constexpr double max_drift_ = .001;
  const double stream_start_;
  double stamp_ = 0., received_ = 0., offset_ = 0.;
  bool initialized_ = false;
};
}  // namespace uwa_cell_protection
