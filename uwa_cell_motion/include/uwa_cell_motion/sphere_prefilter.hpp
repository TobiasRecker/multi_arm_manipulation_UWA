#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace uwa_cell_motion
{
// Bounds enclose complete spheres. Touching/roundoff is always a fine query.
struct SphereAabb
{
  std::array<double,3> low{}, high{};
  bool empty{true};
  void include(double x, double y, double z, double radius)
  {
    if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z) ||
        !std::isfinite(radius) || radius<=0) throw std::runtime_error("Invalid sphere in AABB");
    const std::array<double,3> p{x,y,z};
    for (size_t i=0;i<3;++i) {
      const double lo=std::nextafter(p[i]-radius,-std::numeric_limits<double>::infinity());
      const double hi=std::nextafter(p[i]+radius,std::numeric_limits<double>::infinity());
      low[i]=empty?lo:std::min(low[i],lo); high[i]=empty?hi:std::max(high[i],hi);
    }
    empty=false;
  }
};

inline bool aabbSeparated(const SphereAabb &a,const SphereAabb &b,double threshold)
{
  if (!std::isfinite(threshold) || threshold<0) throw std::runtime_error("Invalid AABB clearance threshold");
  if (a.empty || b.empty) return false;
  double squared=0.,scale_a=0.,scale_b=0.;
  for (size_t i=0;i<3;++i) {
    const double gap=std::max({a.low[i]-b.high[i],b.low[i]-a.high[i],0.});
    squared+=gap*gap;
    scale_a=std::max({scale_a,std::abs(a.low[i]),std::abs(a.high[i])});
    scale_b=std::max({scale_b,std::abs(b.low[i]),std::abs(b.high[i])});
  }
  const double limit=threshold+1e-12*(1+std::abs(threshold)+scale_a+scale_b);
  return squared>limit*limit;
}
}
