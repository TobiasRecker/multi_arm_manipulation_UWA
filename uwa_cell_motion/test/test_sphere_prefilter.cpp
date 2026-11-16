#include <uwa_cell_motion/sphere_prefilter.hpp>
#include <array>
#include <iostream>
#include <random>
#include <vector>
using Sphere=std::array<double,4>;
using uwa_cell_motion::SphereAabb;
bool denseClear(const std::vector<Sphere> &a,const std::vector<Sphere> &b,double margin)
{
  for (const auto &x:a) for (const auto &y:b) {
    double squared=0.;for (int i=0;i<3;++i) squared+=(x[i]-y[i])*(x[i]-y[i]);
    double limit=x[3]+y[3]+margin;if (squared<=limit*limit) return false;
  }
  return true;
}
SphereAabb bounds(const std::vector<Sphere> &spheres)
{
  SphereAabb b;for (const auto &s:spheres)b.include(s[0],s[1],s[2],s[3]);return b;
}
int main()
{
  size_t rejected=0;std::mt19937 rng(20261116);std::uniform_real_distribution<double> position(-2.,2.),radius(.01,.5),margin(0.,.5);
  for (size_t trial=0;trial<3000;++trial) {
    std::vector<Sphere> a,b;
    for (size_t i=0;i<1+trial%17;++i)a.push_back({position(rng),position(rng),position(rng),radius(rng)});
    for (size_t i=0;i<1+trial%23;++i)b.push_back({position(rng)+(trial%2?6.:0.),position(rng),position(rng),radius(rng)});
    const double threshold=margin(rng);bool coarse=uwa_cell_motion::aabbSeparated(bounds(a),bounds(b),threshold);
    if (coarse)++rejected;
    if (coarse && !denseClear(a,b,threshold)) { std::cerr<<"False clear in random native case\n";return 1; }
  }
  for (double offset:{-1e-10,-1e-14,0.,1e-14,1e-10}) {
    std::vector<Sphere> a{{0.,0.,0.,.5}},b{{1.2+offset,0.,0.,.5}};
    if (uwa_cell_motion::aabbSeparated(bounds(a),bounds(b),.2) && !denseClear(a,b,.2)) return 2;
  }
  if (uwa_cell_motion::aabbSeparated(bounds({{0.,0.,0.,2.}}),bounds({{3.,0.,0.,2.}}),.1)) return 3;
  if (rejected<1000) return 4;
  std::cout<<"Native conservative AABB:3000 random plus boundary/volume cases PASS\n";
}
