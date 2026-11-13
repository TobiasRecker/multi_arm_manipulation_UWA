// Optional simulation-only finger hardware. All physical joints receive bounded
// torques, never prescribed positions or velocities. Coupling is an approximate
// compliant servo, not a validated model of the Robotiq adaptive transmission.
#include <algorithm>
#include <atomic>
#include <cmath>
#include <map>
#include <string>
#include <vector>
#include <gz_ros2_control/gz_system_interface.hpp>
#include <gz/sim/components/JointForceCmd.hh>
#include <gz/sim/components/JointPosition.hh>
#include <gz/sim/components/JointVelocity.hh>
#include <gz/sim/components/JointPositionReset.hh>
#include <pluginlib/class_list_macros.hpp>
#include <std_srvs/srv/set_bool.hpp>

namespace uwa_cell_tasks
{
class ContactGripper : public gz_ros2_control::GazeboSimSystemInterface
{
  struct Finger {
    std::string name, driver;
    gz::sim::Entity entity;
    double multiplier{1.}, position{0.}, velocity{0.}, effort{0.};
  };
  gz::sim::EntityComponentManager * ecm_{nullptr};
  std::vector<Finger> fingers_;
  std::map<std::string,double> targets_;
  double kp_{3.}, kd_{.12}, torque_{.35};
  std::atomic<bool> latch_requested_{false};
  bool latched_{false};
  rclcpp::Service<std_srvs::srv::SetBool>::SharedPtr latch_service_;
public:
  hardware_interface::CallbackReturn on_init(
    const hardware_interface::HardwareComponentInterfaceParams & params) override
  {
    return hardware_interface::SystemInterface::on_init(params);
  }
  bool initSim(rclcpp::Node::SharedPtr & node,
    std::map<std::string,gz::sim::Entity> & joints,
    const hardware_interface::HardwareInfo & info,
    gz::sim::EntityComponentManager & ecm, unsigned int) override
  {
    ecm_=&ecm;
    try {
      kp_=std::stod(info.hardware_parameters.at("kp"));
      kd_=std::stod(info.hardware_parameters.at("kd"));
      torque_=std::stod(info.hardware_parameters.at("max_torque"));
      if (!std::isfinite(kp_+kd_+torque_) || kp_<=0 || kd_<=0 || torque_<=0) return false;
      for (const auto & joint:info.joints) {
        Finger f; f.name=joint.name; f.entity=joints.at(joint.name);
        f.driver=joint.parameters.at("driver");
        if (joint.parameters.count("multiplier")) f.multiplier=std::stod(joint.parameters.at("multiplier"));
        if (joint.command_interfaces.size()) targets_[f.name]=0.;
        if (!ecm.Component<gz::sim::components::JointPosition>(f.entity))
          ecm.CreateComponent(f.entity,gz::sim::components::JointPosition());
        if (!ecm.Component<gz::sim::components::JointVelocity>(f.entity))
          ecm.CreateComponent(f.entity,gz::sim::components::JointVelocity());
        if (!ecm.Component<gz::sim::components::JointForceCmd>(f.entity))
          ecm.CreateComponent(f.entity,gz::sim::components::JointForceCmd({0.}));
        fingers_.push_back(f);
      }
      for (const auto & f:fingers_) if (!targets_.count(f.driver)) return false;
      latch_service_=node->create_service<std_srvs::srv::SetBool>(
        "tasks/grip_latch",[this](const std::shared_ptr<std_srvs::srv::SetBool::Request> req,
          std::shared_ptr<std_srvs::srv::SetBool::Response> res) {
          latch_requested_.store(req->data); res->success=true;
          res->message=req->data ? "Grip target retained independently of arm holds" : "Grip target released; no open command sent";
        });
      return true;
    } catch (const std::exception & e) {RCLCPP_ERROR(node->get_logger(),"Contact gripper: %s",e.what());return false;}
  }
  hardware_interface::CallbackReturn on_activate(const rclcpp_lifecycle::State &) override
  {
    for (const auto & f:fingers_) {
      set_state(f.name+"/position",0.);set_state(f.name+"/velocity",0.);set_state(f.name+"/effort",0.);
    }
    for (const auto & target:targets_) set_command(target.first+"/position",0.);
    return hardware_interface::CallbackReturn::SUCCESS;
  }
  hardware_interface::return_type read(const rclcpp::Time &,const rclcpp::Duration &) override
  {
    for (auto & f:fingers_) {
      auto q=ecm_->Component<gz::sim::components::JointPosition>(f.entity);
      auto v=ecm_->Component<gz::sim::components::JointVelocity>(f.entity);
      if (q && !q->Data().empty()) f.position=q->Data()[0];
      if (v && !v->Data().empty()) f.velocity=v->Data()[0];
      set_state(f.name+"/position",f.position);set_state(f.name+"/velocity",f.velocity);
      set_state(f.name+"/effort",f.effort); // applied actuator torque, not inferred contact force
    }
    return hardware_interface::return_type::OK;
  }
  hardware_interface::return_type write(const rclcpp::Time &,const rclcpp::Duration & period) override
  {
    const bool latch=latch_requested_.load();
    {
      for (auto & target:targets_) {
        // Explicit grip latch ramps toward closed-air target under bounded
        // torque. It retains preload through controller cancellation/arm holds.
        const double q=latch ? .8 : get_command(target.first+"/position");
        if (!std::isfinite(q)) return hardware_interface::return_type::ERROR;
        const double step=.02*std::max(0.,period.seconds());
        target.second+=std::clamp(std::clamp(q,0.,.8)-target.second,-step,step);
      }
    }
    latched_=latch;
    for (auto & f:fingers_) {
      const double desired=targets_.at(f.driver)*f.multiplier;
      f.effort=std::clamp(kp_*(desired-f.position)-kd_*f.velocity,-torque_,torque_);
      ecm_->Component<gz::sim::components::JointForceCmd>(f.entity)->Data()={f.effort};
    }
    return hardware_interface::return_type::OK;
  }
};
}
PLUGINLIB_EXPORT_CLASS(uwa_cell_tasks::ContactGripper,gz_ros2_control::GazeboSimSystemInterface)
