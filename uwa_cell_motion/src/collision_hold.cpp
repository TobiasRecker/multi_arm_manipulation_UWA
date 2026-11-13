#include <algorithm>
#include <cmath>
#include <string>
#include <vector>
#include <controller_interface/controller_interface.hpp>
#include <pluginlib/class_list_macros.hpp>

namespace uwa_cell_motion
{
// No command subscription: once active, this controller owns the arm interfaces
// until the supervisor explicitly releases it. Topic commands cannot move it.
class CollisionHold : public controller_interface::ControllerInterface
{
  std::vector<std::string> joints_;
  std::vector<double> q_, v_;
  double deceleration_{0.5};
public:
  controller_interface::CallbackReturn on_init() override
  {
    try {
      joints_ = auto_declare<std::vector<std::string>>("joints", {});
      deceleration_ = auto_declare<double>("deceleration", 0.5);
      if (joints_.empty() || !std::isfinite(deceleration_) || deceleration_ <= 0)
        return controller_interface::CallbackReturn::ERROR;
      q_.resize(joints_.size()); v_.resize(joints_.size());
    } catch (...) { return controller_interface::CallbackReturn::ERROR; }
    return controller_interface::CallbackReturn::SUCCESS;
  }
  controller_interface::InterfaceConfiguration command_interface_configuration() const override
  {
    controller_interface::InterfaceConfiguration c{controller_interface::interface_configuration_type::INDIVIDUAL, {}};
    for (const auto & j : joints_) c.names.push_back(j + "/position");
    return c;
  }
  controller_interface::InterfaceConfiguration state_interface_configuration() const override
  {
    controller_interface::InterfaceConfiguration c{controller_interface::interface_configuration_type::INDIVIDUAL, {}};
    for (const auto & j : joints_) { c.names.push_back(j + "/position"); c.names.push_back(j + "/velocity"); }
    return c;
  }
  controller_interface::CallbackReturn on_activate(const rclcpp_lifecycle::State &) override
  {
    for (size_t i=0; i<joints_.size(); ++i) {
      q_[i] = state_interfaces_[2*i].get_optional().value_or(NAN);
      v_[i] = state_interfaces_[2*i+1].get_optional().value_or(NAN);
      if (!std::isfinite(q_[i]) || !std::isfinite(v_[i])) return controller_interface::CallbackReturn::ERROR;
    }
    return controller_interface::CallbackReturn::SUCCESS;
  }
  controller_interface::return_type update(const rclcpp::Time &, const rclcpp::Duration & period) override
  {
    const double dt = period.seconds();
    for (size_t i=0; i<q_.size(); ++i) {
      const double next = std::copysign(std::max(0.0, std::abs(v_[i])-deceleration_*dt), v_[i]);
      q_[i] += 0.5*(v_[i]+next)*dt;
      v_[i] = next;
      if (!command_interfaces_[i].set_value(q_[i])) return controller_interface::return_type::ERROR;
    }
    return controller_interface::return_type::OK;
  }
};
}
PLUGINLIB_EXPORT_CLASS(uwa_cell_motion::CollisionHold, controller_interface::ControllerInterface)
