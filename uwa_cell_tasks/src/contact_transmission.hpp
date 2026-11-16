#pragma once
#include <algorithm>
#include <utility>

namespace uwa_cell_tasks {
// Elastic gear constraint. The reaction acts on the driver, so internal
// coupling adds no motor/energy source and damping always dissipates energy.
inline std::pair<double,double> transmission_torques(
  double driver_q,double driver_v,double passive_q,double passive_v,
  double ratio,double stiffness,double damping,double torque_limit)
{
  const double passive=std::clamp(stiffness*(ratio*driver_q-passive_q)+
    damping*(ratio*driver_v-passive_v),-torque_limit,torque_limit);
  return {passive,-ratio*passive};
}
}
