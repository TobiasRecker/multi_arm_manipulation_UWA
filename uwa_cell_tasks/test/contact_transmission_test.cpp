#include <cmath>
#include <iostream>
#include "contact_transmission.hpp"
int main()
{
  using uwa_cell_tasks::transmission_torques;
  for(const double ratio:{-1.,1.}) {
    const auto aligned=transmission_torques(.3,.02,ratio*.3,ratio*.02,ratio,3.,.003,.35);
    if(std::abs(aligned.first)+std::abs(aligned.second)>1e-12)return 1;
    const auto loaded=transmission_torques(.5,.02,.1,.01,ratio,3.,.003,.35);
    if(std::abs(ratio*loaded.first+loaded.second)>1e-12 || std::abs(loaded.first)>.35)return 2;
    for(const double passive_v:{-.1,0.,.1}) {
      const auto viscous=transmission_torques(0.,.02,0.,passive_v,ratio,0.,.003,.35);
      const double power=viscous.first*passive_v+viscous.second*.02;
      if(power>1e-12 || std::abs(power+.003*std::pow(passive_v-ratio*.02,2))>1e-12)return 3;
    }
  }
  std::cout<<"PASS: aligned gears, driver reaction, bounded coupling and dissipative damping\n";
}
