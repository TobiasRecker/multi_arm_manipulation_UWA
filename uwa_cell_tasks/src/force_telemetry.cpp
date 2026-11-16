// Opt-in load observation, separate from the existing contact/clock guard path.
// Contact body identity is deliberately NOT inferred from reordered collision IDs.
#include <chrono>
#include <array>
#include <cmath>
#include <iomanip>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <nlohmann/json.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>
#include <gz/plugin/Register.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/ContactSensorData.hh>
#include <gz/sim/components/Joint.hh>
#include <gz/sim/components/JointTransmittedWrench.hh>
#include <gz/sim/components/Name.hh>

namespace uwa_cell_tasks {
using Json=nlohmann::json;
struct LoadWindow {
  double normal_integral{0.},tangent_integral{0.},peak_normal{0.},peak_tangent{0.};
  std::array<double,3> force_integral{},torque_integral{};
  double peak_force_norm{0.},peak_torque_norm{0.};
};

class ForceTelemetry:public gz::sim::System,public gz::sim::ISystemConfigure,
  public gz::sim::ISystemPreUpdate {
  std::string namespace_,object_;
  std::set<std::string> requested_;
  std::map<std::string,gz::sim::Entity> joints_;
  std::map<std::string,LoadWindow> pair_windows_,joint_windows_;
  std::map<std::string,Json> pairs_,joint_last_;
  rclcpp::Node::SharedPtr node_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
  double elapsed_{0.},window_start_{0.};
  size_t samples_{0},duplicates_{0},missing_{0},invalid_{0};
public:
  void Configure(const gz::sim::Entity &,const std::shared_ptr<const sdf::Element> & s,
    gz::sim::EntityComponentManager &,gz::sim::EventManager &) override {
    namespace_=s->Get<std::string>("ros_namespace");object_=s->Get<std::string>("object_model");
    if(namespace_.rfind("/uwa_grasp_",0)!=0)throw std::runtime_error("Private simulation namespace required");
    std::istringstream input(s->Get<std::string>("joints"));std::string name;
    while(input>>name)requested_.insert(name);
  }
  void PreUpdate(const gz::sim::UpdateInfo & info,gz::sim::EntityComponentManager & ecm) override {
    if(info.paused || !rclcpp::ok())return;
    if(!node_) {
      node_=std::make_shared<rclcpp::Node>("task_force_telemetry",namespace_);
      publisher_=node_->create_publisher<std_msgs::msg::String>("tasks/forces",rclcpp::QoS(1).best_effort());
    }
    if(joints_.size()<requested_.size()) {
      ecm.Each<gz::sim::components::Name,gz::sim::components::Joint>(
        [&](const auto & entity,const auto * name,const auto *) {
          if(requested_.count(name->Data())) {
            joints_[name->Data()]=entity;
            if(!ecm.Component<gz::sim::components::JointTransmittedWrench>(entity))
              ecm.CreateComponent(entity,gz::sim::components::JointTransmittedWrench());
          }return true;
        });
    }
    const double dt=std::chrono::duration<double>(info.dt).count();if(dt<=0)return;
    const double stamp=std::max(0.,std::chrono::duration<double>(info.simTime-info.dt).count());
    if(samples_==0)window_start_=stamp;
    std::map<std::string,std::pair<double,double>> totals;
    std::map<std::string,const gz::msgs::Contact *> selected;
    std::map<std::string,std::string> selected_owner;
    ecm.Each<gz::sim::components::ContactSensorData>(
      [&](const auto &,const auto * data) {
        for(const auto & c:data->Data().contact()) {
          const auto a=gz::sim::scopedName(c.collision1().id(),ecm,"::");
          const auto b=gz::sim::scopedName(c.collision2().id(),ecm,"::");
          if(a.find(object_)==std::string::npos && b.find(object_)==std::string::npos)continue;
          const std::string pair=std::min(a,b)+"|"+std::max(a,b);
          pairs_[pair]={{"collisions",{std::min(a,b),std::max(a,b)}}};
          if(selected.count(pair)) {
            ++duplicates_;
            if(a>=selected_owner[pair])continue;
          }
          selected[pair]=&c;selected_owner[pair]=a;
        }return true;
      });
    // Whole-pair selection is essential: component-local cached positions may
    // differ by1um, so point-coordinate deduplication can double count impulse.
    for(const auto & [pair,source]:selected) {
          const auto & c=*source;
          for(int i=0;i<c.position_size();++i) {
            if(i>=c.wrench_size() || i>=c.normal_size()) {++missing_;continue;}
            const auto & p=c.position(i);const auto & raw=c.wrench(i).body_1_wrench().force();
            const auto & opposite=c.wrench(i).body_2_wrench().force();const auto & normal=c.normal(i);
            gz::math::Vector3d f(raw.x(),raw.y(),raw.z()),other(opposite.x(),opposite.y(),opposite.z()),n(normal.x(),normal.y(),normal.z());
            if(!f.IsFinite() || !other.IsFinite() || !n.IsFinite() || n.Length()<.99 || (f+other).Length()>1e-5) {++invalid_;continue;}
            n.Normalize();
            const double fn=std::abs(f.Dot(n));const double ft=(f-n*f.Dot(n)).Length();
            totals[pair].first+=fn;totals[pair].second+=ft;
          }
    }
    for(const auto & [pair,load]:totals) {
      auto & stats=pair_windows_[pair];stats.normal_integral+=load.first*dt;stats.tangent_integral+=load.second*dt;
      stats.peak_normal=std::max(stats.peak_normal,load.first);stats.peak_tangent=std::max(stats.peak_tangent,load.second);
    }
    for(const auto & [name,entity]:joints_) {
      const auto * component=ecm.Component<gz::sim::components::JointTransmittedWrench>(entity);
      if(!component) {++missing_;continue;}
      const auto & w=component->Data();const auto & f=w.force();const auto & t=w.torque();
      gz::math::Vector3d force(f.x(),f.y(),f.z()),torque(t.x(),t.y(),t.z());
      if(!force.IsFinite() || !torque.IsFinite()) {++invalid_;continue;}
      auto & stats=joint_windows_[name];for(int i=0;i<3;++i) {stats.force_integral[i]+=force[i]*dt;stats.torque_integral[i]+=torque[i]*dt;}
      stats.peak_force_norm=std::max(stats.peak_force_norm,force.Length());stats.peak_torque_norm=std::max(stats.peak_torque_norm,torque.Length());
      joint_last_[name]={{"force_n",{force.X(),force.Y(),force.Z()}},{"torque_nm",{torque.X(),torque.Y(),torque.Z()}},{"frame","joint:"+name}};
    }
    elapsed_+=dt;++samples_;
    if(elapsed_<.01-1e-9)return;
    Json contacts=Json::array(),joints=Json::object();
    for(const auto & [pair,stats]:pair_windows_) {
      auto row=pairs_[pair];row["mean_normal_load_n"]=stats.normal_integral/elapsed_;row["peak_normal_load_n"]=stats.peak_normal;
      row["mean_tangential_load_n"]=stats.tangent_integral/elapsed_;row["peak_tangential_load_n"]=stats.peak_tangent;
      row["normal_impulse_ns"]=stats.normal_integral;row["tangential_load_integral_ns"]=stats.tangent_integral;contacts.push_back(row);
    }
    for(const auto & [name,stats]:joint_windows_) {
      auto row=joint_last_[name];Json f=Json::array(),t=Json::array();
      for(int i=0;i<3;++i) {f.push_back(stats.force_integral[i]/elapsed_);t.push_back(stats.torque_integral[i]/elapsed_);}
      row["mean_force_n"]=f;row["mean_torque_nm"]=t;row["peak_force_norm_n"]=stats.peak_force_norm;row["peak_torque_norm_nm"]=stats.peak_torque_norm;joints[name]=row;
    }
    Json report={{"schema_version",1},{"source","native_physics_ecm"},{"stamp",stamp},
      {"stamp_kind","completed_previous_physics_step"},{"window_start_s",window_start_},{"window_duration_s",elapsed_},
      {"physics_samples",samples_},{"duplicate_manifolds_removed",duplicates_},{"missing_wrenches",missing_},{"invalid_wrenches",invalid_},
      {"contact_body_attribution_trusted",false},{"contact_loads",contacts},{"joint_reactions",joints},
      {"requested_joints",requested_},{"found_joints",joints_.size()},{"interpretation","Unsigned contact loads and joint-frame reactions; no material damage or hardware qualification."}};
    std_msgs::msg::String message;message.data=report.dump();publisher_->publish(message);
    elapsed_=0.;samples_=duplicates_=missing_=invalid_=0;pair_windows_.clear();pairs_.clear();joint_windows_.clear();joint_last_.clear();
  }
};
}
GZ_ADD_PLUGIN(uwa_cell_tasks::ForceTelemetry,gz::sim::System,gz::sim::ISystemConfigure,gz::sim::ISystemPreUpdate)
