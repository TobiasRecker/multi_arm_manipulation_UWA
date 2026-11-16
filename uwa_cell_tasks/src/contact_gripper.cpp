// Optional simulation-only finger hardware. All physical joints receive bounded
// torques, never prescribed positions or velocities. Coupling is an approximate
// compliant servo, not a validated model of the Robotiq adaptive transmission.
#include <algorithm>
#include <atomic>
#include <cmath>
#include <map>
#include <string>
#include <vector>
#include <iostream>
#include "contact_transmission.hpp"
#include <gz_ros2_control/gz_system_interface.hpp>
#include <gz/sim/components/JointForceCmd.hh>
#include <gz/sim/components/JointPosition.hh>
#include <gz/sim/components/JointVelocity.hh>
#include <gz/sim/components/JointPositionReset.hh>
#include <gz/sim/components/JointVelocityCmd.hh>
#include <gz/sim/components/Factory.hh>
#include <gz/plugin/Register.hh>
#include <pluginlib/class_list_macros.hpp>
#include <std_srvs/srv/set_bool.hpp>

namespace uwa_cell_tasks
{
using ServoTarget=gz::sim::components::Component<std::vector<double>,class ServoTargetTag>;
GZ_SIM_REGISTER_COMPONENT("uwa_cell_tasks.components.ServoTarget",ServoTarget)
using ArmTarget=gz::sim::components::Component<std::vector<double>,class ArmTargetTag>;
GZ_SIM_REGISTER_COMPONENT("uwa_cell_tasks.components.ArmTarget",ArmTarget)

// Physics-rate inner loop. ros2_control's write period can be slower than the
// physics step even with a 1kHz manager; holding a high-gain torque for that
// entire interval excites the tiny finger inertias during arm motion.
class ContactServoSystem : public gz::sim::System, public gz::sim::ISystemPreUpdate
{
  bool reported_{false},moving_{false};
public:
  void PreUpdate(const gz::sim::UpdateInfo & info,gz::sim::EntityComponentManager & ecm) override
  {
    if (info.paused) return;
    const double dt=std::chrono::duration<double>(info.dt).count();
    std::map<gz::sim::Entity,double> finger_torques;
    ecm.Each<ServoTarget,gz::sim::components::JointPosition,gz::sim::components::JointVelocity>(
      [dt,&ecm,&finger_torques](const gz::sim::Entity & entity,ServoTarget * target,
        const gz::sim::components::JointPosition * q,const gz::sim::components::JointVelocity * v) {
        auto & t=target->Data();
        if(t.size()!=13 || q->Data().empty() || v->Data().empty())return true;
        t[11]=0.;
        if(t[10]>0.) {
          const double step=(t[0]>t[4] && t[4]>=t[7] ? t[6] : t[5])*dt;
          t[4]+=std::clamp(t[0]-t[4],-step,step);
          t[11]=std::clamp(t[12]*(t[4]-q->Data()[0])-t[2]*v->Data()[0],-t[3],t[3]);
          finger_torques[entity]+=t[11];
        } else {
          const auto driver=static_cast<gz::sim::Entity>(t[8]);
          const auto dq=ecm.Component<gz::sim::components::JointPosition>(driver);
          const auto dv=ecm.Component<gz::sim::components::JointVelocity>(driver);
          if(!dq || !dv || dq->Data().empty() || dv->Data().empty())return true;
          const auto torque=transmission_torques(dq->Data()[0],dv->Data()[0],q->Data()[0],v->Data()[0],t[9],t[1],t[2],t[3]);
          finger_torques[entity]+=torque.first;finger_torques[driver]+=torque.second;
        }
        return true;
      });
    for(const auto & entry:finger_torques)
      ecm.SetComponentData<gz::sim::components::JointForceCmd>(entry.first,{entry.second});
    size_t arm_count=0;
    ecm.Each<ArmTarget,gz::sim::components::JointPosition>(
      [this,dt,&arm_count,&ecm](const gz::sim::Entity & entity,ArmTarget * target,
        const gz::sim::components::JointPosition * q) {
        auto & t=target->Data();
        if(t.size()!=6 || q->Data().empty())return true;
        ++arm_count;
        // The stock position backend uses a ROS-read cached position. A
        // substep servo instead uses this physics step's actual state, with
        // bounded actuator speed and acceleration, avoiding sampled impulses
        // into passive contact fingers. This is an actuator, not a planner.
        // Predict the same shared reference between controller samples using
        // its supplied derivative. Position-only stair steps excite passive
        // fingers even when their endpoints follow the correct path.
        const double desired=std::clamp(t[1]+30.*(t[0]+t[1]*t[2]-q->Data()[0]),-t[4],t[4]);
        t[3]+=std::clamp(desired-t[3],-t[5]*dt,t[5]*dt);t[2]+=dt;
        if(!moving_ && std::abs(t[3])>.001) {
          moving_=true;std::cerr<<"CONTACT SERVO: first motion target="<<t[0]<<" measured="<<q->Data()[0]<<" velocity="<<t[3]<<std::endl;
        }
        // Physics consumes/removes JointVelocityCmd each step. Recreate it;
        // requiring it in this Each view would silently lose the actuator.
        ecm.SetComponentData<gz::sim::components::JointVelocityCmd>(entity,{t[3]});return true;
      });
    if(!reported_ && arm_count) {reported_=true;std::cerr<<"CONTACT SERVO READY: "<<arm_count<<" arm joints"<<std::endl;}
  }
};

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
  double kp_{3.}, motor_kp_{10.}, kd_{.003}, torque_{.35},motor_torque_{.35};
  double coarse_{.02},fine_{.004},fine_start_{.65};
  std::atomic<bool> latch_requested_{false};
  bool latched_{false};
  bool native_mimic_{true};
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
      motor_kp_=std::stod(info.hardware_parameters.at("motor_kp"));
      kd_=std::stod(info.hardware_parameters.at("kd"));
      torque_=std::stod(info.hardware_parameters.at("max_torque"));
      motor_torque_=info.hardware_parameters.count("motor_max_torque") ?
        std::stod(info.hardware_parameters.at("motor_max_torque")):torque_;
      coarse_=std::stod(info.hardware_parameters.at("coarse_velocity"));
      fine_=std::stod(info.hardware_parameters.at("fine_velocity"));
      fine_start_=std::stod(info.hardware_parameters.at("fine_start"));
      native_mimic_=info.hardware_parameters.at("native_mimic")=="true";
      if (!std::isfinite(kp_+motor_kp_+kd_+torque_+motor_torque_) || kp_<=0 || motor_kp_<=0 || kd_<=0 || torque_<=0 || motor_torque_<=0) return false;
      const double limit=info.hardware_parameters.count("velocity_limit") ? std::stod(info.hardware_parameters.at("velocity_limit")):.05;
      if(!std::isfinite(coarse_+fine_+fine_start_+limit) || limit<=0 || limit>2. || fine_<=0 || fine_>coarse_ || coarse_>limit || fine_start_<=0 || fine_start_>=.8)return false;
      for (const auto & joint:info.joints) {
        Finger f; f.name=joint.name; f.entity=joints.at(joint.name);
        f.driver=joint.parameters.at("driver");
        if (joint.parameters.count("multiplier")) f.multiplier=std::stod(joint.parameters.at("multiplier"));
        if (joint.command_interfaces.size()) targets_[f.name]=0.;
        if (!ecm.Component<gz::sim::components::JointPosition>(f.entity))
          ecm.CreateComponent(f.entity,gz::sim::components::JointPosition());
        if (!ecm.Component<gz::sim::components::JointVelocity>(f.entity))
          ecm.CreateComponent(f.entity,gz::sim::components::JointVelocity());
        // Native gear constraints transmit reactions in the physics solver.
        // Only the driver is actuated; passive states are still measured.
        if(f.name==f.driver || !native_mimic_) {
          if (!ecm.Component<gz::sim::components::JointForceCmd>(f.entity))
            ecm.CreateComponent(f.entity,gz::sim::components::JointForceCmd({0.}));
          ecm.CreateComponent(f.entity,ServoTarget({0.,kp_,kd_,f.name==f.driver ? motor_torque_:torque_,0.,coarse_,fine_,fine_start_,
            static_cast<double>(joints.at(f.driver)),f.multiplier,f.name==f.driver ? 1. : 0.,0.,motor_kp_}));
        }
        fingers_.push_back(f);
      }
      for (const auto & f:fingers_) if (!targets_.count(f.driver)) return false;
      RCLCPP_INFO(node->get_logger(),"CONTACT TRANSMISSION: %s; one torque-limited motor per gripper",
        native_mimic_ ? "native physics gear constraints" : "experimental elastic gears");
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
      auto target=ecm_->Component<ServoTarget>(f.entity);
      if(target && target->Data().size()==13)f.effort=target->Data()[11];
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
        const double step=coarse_*std::max(0.,period.seconds());
        target.second+=std::clamp(std::clamp(q,0.,.8)-target.second,-step,step);
      }
    }
    latched_=latch;
    for (auto & f:fingers_) {
      const double desired=targets_.at(f.driver)*f.multiplier;
      auto servo=ecm_->Component<ServoTarget>(f.entity);
      if(servo)servo->Data()[0]=desired;
    }
    return hardware_interface::return_type::OK;
  }
};

class ContactArms : public gz_ros2_control::GazeboSimSystemInterface
{
  struct Joint {std::string name;gz::sim::Entity entity;double initial;bool velocity_mode{false};};
  std::vector<Joint> joints_;
  gz::sim::EntityComponentManager * ecm_{nullptr};
public:
  hardware_interface::CallbackReturn on_init(
    const hardware_interface::HardwareComponentInterfaceParams & params) override
  {return hardware_interface::SystemInterface::on_init(params);}
  bool initSim(rclcpp::Node::SharedPtr &,std::map<std::string,gz::sim::Entity> & entities,
    const hardware_interface::HardwareInfo & info,gz::sim::EntityComponentManager & ecm,unsigned int) override
  {
    ecm_=&ecm;
    try {
      const double max_v=info.hardware_parameters.count("max_velocity") ? std::stod(info.hardware_parameters.at("max_velocity")):.05;
      const double max_a=info.hardware_parameters.count("max_acceleration") ? std::stod(info.hardware_parameters.at("max_acceleration")):.5;
      if(!std::isfinite(max_v+max_a) || max_v<=0 || max_v>1. || max_a<=0 || max_a>5.)return false;
      for(const auto & j:info.joints) {
        double initial=0.;
        for(const auto & s:j.state_interfaces)if(s.name=="position" && !s.initial_value.empty())initial=std::stod(s.initial_value);
        if(!std::isfinite(initial))return false;
        const auto entity=entities.at(j.name);joints_.push_back({j.name,entity,initial});
        ecm.CreateComponent(entity,gz::sim::components::JointPositionReset({initial}));
        if(!ecm.Component<gz::sim::components::JointPosition>(entity))ecm.CreateComponent(entity,gz::sim::components::JointPosition());
        if(!ecm.Component<gz::sim::components::JointVelocity>(entity))ecm.CreateComponent(entity,gz::sim::components::JointVelocity());
        ecm.CreateComponent(entity,gz::sim::components::JointVelocityCmd({0.}));
        ecm.CreateComponent(entity,ArmTarget({initial,0.,0.,0.,max_v,max_a}));
      }
      return true;
    } catch(...) {return false;}
  }
  hardware_interface::CallbackReturn on_activate(const rclcpp_lifecycle::State &) override
  {
    for(const auto & j:joints_) {
      set_state(j.name+"/position",j.initial);set_state(j.name+"/velocity",0.);
      set_command(j.name+"/position",j.initial);
      set_command(j.name+"/velocity",0.);
    }
    return hardware_interface::CallbackReturn::SUCCESS;
  }
  hardware_interface::return_type read(const rclcpp::Time &,const rclcpp::Duration &) override
  {
    for(const auto & j:joints_) {
      auto q=ecm_->Component<gz::sim::components::JointPosition>(j.entity);
      auto v=ecm_->Component<gz::sim::components::JointVelocity>(j.entity);
      if(q && !q->Data().empty())set_state(j.name+"/position",q->Data()[0]);
      if(v && !v->Data().empty())set_state(j.name+"/velocity",v->Data()[0]);
    }
    return hardware_interface::return_type::OK;
  }
  hardware_interface::return_type write(const rclcpp::Time &,const rclcpp::Duration &) override
  {
    for(const auto & j:joints_) {
      const double q=get_command(j.name+"/position");
      const double v=j.velocity_mode ? get_command(j.name+"/velocity") : 0.;
      if(!std::isfinite(q) || !std::isfinite(v))return hardware_interface::return_type::ERROR;
      auto & t=ecm_->Component<ArmTarget>(j.entity)->Data();
      if(q!=t[0] || v!=t[1]) {t[0]=q;t[1]=v;t[2]=0.;}
    }
    return hardware_interface::return_type::OK;
  }
  hardware_interface::return_type perform_command_mode_switch(
    const std::vector<std::string> & start,const std::vector<std::string> & stop) override
  {
    for(auto & j:joints_) {
      if(std::find(stop.begin(),stop.end(),j.name+"/velocity")!=stop.end())j.velocity_mode=false;
      if(std::find(start.begin(),start.end(),j.name+"/velocity")!=start.end())j.velocity_mode=true;
    }
    return hardware_interface::return_type::OK;
  }
};
}
PLUGINLIB_EXPORT_CLASS(uwa_cell_tasks::ContactGripper,gz_ros2_control::GazeboSimSystemInterface)
PLUGINLIB_EXPORT_CLASS(uwa_cell_tasks::ContactArms,gz_ros2_control::GazeboSimSystemInterface)
GZ_ADD_PLUGIN(uwa_cell_tasks::ContactServoSystem,gz::sim::System,gz::sim::ISystemPreUpdate)
