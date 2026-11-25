// Publish actual ECM state directly to private ROS topics. Gazebo Transport
// queues are deliberately absent from the runtime clock/contact safety path.
#include <chrono>
#include <string>
#include <nlohmann/json.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>
#include <rosgraph_msgs/msg/clock.hpp>
#include <gz/plugin/RegisterMore.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/ContactSensorData.hh>
#include <gz/sim/components/Model.hh>
#include <gz/sim/components/Name.hh>

namespace uwa_cell_tasks {
class TaskTelemetry : public gz::sim::System,public gz::sim::ISystemConfigure,public gz::sim::ISystemPreUpdate
{
  std::string namespace_;
  std::string object_model_;
  rclcpp::Node::SharedPtr node_;
  rclcpp::Publisher<rosgraph_msgs::msg::Clock>::SharedPtr clock_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr contacts_,pose_;
  int64_t last_{-10000000};
  gz::sim::Entity object_{gz::sim::kNullEntity};
public:
  void Configure(const gz::sim::Entity &,const std::shared_ptr<const sdf::Element> & sdf,
    gz::sim::EntityComponentManager &,gz::sim::EventManager &) override
  {
    namespace_=sdf->Get<std::string>("ros_namespace");
    object_model_=sdf->Get<std::string>("object_model", "uwa_grasp_carton").first;
    if(namespace_.rfind("/uwa_grasp_",0)!=0)throw std::runtime_error("Private task telemetry namespace required");
  }
  void PreUpdate(const gz::sim::UpdateInfo & info,gz::sim::EntityComponentManager & ecm) override
  {
    if(info.paused || !rclcpp::ok())return;
    if(!node_) {
      node_=std::make_shared<rclcpp::Node>("task_physics_telemetry",namespace_);
      clock_=node_->create_publisher<rosgraph_msgs::msg::Clock>("clock",rclcpp::QoS(1).best_effort());
      // Continuous latest-state streams must not back-pressure the physics
      // thread while a receiver renders/processes an image. Independent wall
      // watchdogs still reject missing/stale samples; no cached pose is renewed.
      contacts_=node_->create_publisher<std_msgs::msg::String>("tasks/contacts",rclcpp::QoS(1).best_effort());
      pose_=node_->create_publisher<std_msgs::msg::String>("tasks/object_truth",rclcpp::QoS(1).best_effort());
      RCLCPP_INFO(node_->get_logger(),"NATIVE TELEMETRY READY: physics clock, actual object and contact state at100Hz");
    }
    const int64_t stamp=std::chrono::duration_cast<std::chrono::nanoseconds>(info.simTime).count();
    if(stamp>=last_ && stamp-last_<10000000)return;
    last_=stamp;rosgraph_msgs::msg::Clock time;
    time.clock.sec=stamp/1000000000LL;time.clock.nanosec=stamp%1000000000LL;clock_->publish(time);
    if(object_==gz::sim::kNullEntity || !ecm.HasEntity(object_))
      object_=ecm.EntityByComponents(gz::sim::components::Name(object_model_),gz::sim::components::Model());
    if(object_==gz::sim::kNullEntity)return;
    // PreUpdate reads the completed previous physics result, not a predicted
    // pose or a synthetic attachment. Label that one-step-old measurement.
    const double measured_stamp=std::max(0.,std::chrono::duration<double>(info.simTime-info.dt).count());
    using Json=nlohmann::json;
    const auto actual=gz::sim::worldPose(object_,ecm);
    const gz::math::Matrix3d rotation(actual.Rot());
    Json transform=Json::array();
    for(int row=0;row<3;++row)transform.push_back({rotation(row,0),rotation(row,1),rotation(row,2),actual.Pos()[row]});
    transform.push_back({0.,0.,0.,1.});
    Json truth={{"T_world_object",transform},{"source","simulation_ground_truth"},{"stamp",measured_stamp},
      {"stamp_source","previous_native_physics_result"}};
    std_msgs::msg::String message;message.data=truth.dump();pose_->publish(message);
    Json pads={{"right_front",{{"left_pad",false},{"right_pad",false}}},
               {"right_rear",{{"left_pad",false},{"right_pad",false}}}};
    bool supported=false;Json records=Json::array();
    ecm.Each<gz::sim::components::ContactSensorData>(
      [&](const gz::sim::Entity &,const gz::sim::components::ContactSensorData * data) {
        for(const auto & contact:data->Data().contact()) {
          const std::string a=gz::sim::scopedName(contact.collision1().id(),ecm,"::");
          const std::string b=gz::sim::scopedName(contact.collision2().id(),ecm,"::");
          if(a.find(object_model_)==std::string::npos && b.find(object_model_)==std::string::npos)continue;
          supported=supported || a.find("table_plate")!=std::string::npos || b.find("table_plate")!=std::string::npos;
          for(const std::string arm:{"right_front","right_rear"})for(const std::string side:{"left","right"}) {
            const std::string name=arm+"_robotiq_85_"+side+"_finger_tip_pad";
            if(a.find(name)!=std::string::npos || b.find(name)!=std::string::npos)pads[arm][side+"_pad"]=true;
          }
          Json positions=Json::array(),normals=Json::array(),depths=Json::array();
          for(const auto & p:contact.position())positions.push_back({p.x(),p.y(),p.z()});
          for(const auto & n:contact.normal())normals.push_back({n.x(),n.y(),n.z()});
          for(const auto d:contact.depth())depths.push_back(d);
          records.push_back({{"collisions",{a,b}},{"positions",positions},{"normals",normals},{"depths",depths}});
        }
        return true;
      });
    Json contact={{"pads",pads},{"supported",supported},{"contacts",records},{"stamp",measured_stamp},
      {"stamp_source","previous_native_physics_result"}};
    message.data=contact.dump();contacts_->publish(message);
  }
};
}
GZ_ADD_PLUGIN(uwa_cell_tasks::TaskTelemetry,gz::sim::System,gz::sim::ISystemConfigure,gz::sim::ISystemPreUpdate)
