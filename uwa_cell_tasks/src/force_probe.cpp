// Isolated known-load reference experiment. No ROS or robot controllers.
#include <algorithm>
#include <chrono>
#include <fstream>
#include <map>
#include <string>
#include <nlohmann/json.hpp>
#include <gz/plugin/Register.hh>
#include <gz/sim/Link.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Util.hh>
#include <gz/sim/components/ContactSensorData.hh>
#include <gz/sim/components/ExternalWorldWrenchCmd.hh>
#include <gz/sim/components/Joint.hh>
#include <gz/sim/components/JointTransmittedWrench.hh>
#include <gz/sim/components/Link.hh>
#include <gz/sim/components/Name.hh>

namespace uwa_cell_tasks {
using Json=nlohmann::json;
static Json vector(const gz::math::Vector3d & v) {return {v.X(),v.Y(),v.Z()};}
static Json vector(const gz::msgs::Vector3d & v) {return {v.x(),v.y(),v.z()};}
static Json wrench(const gz::msgs::Wrench & w) {
  return {{"force",vector(w.force())},{"torque",vector(w.torque())}};
}

class ForceProbe:public gz::sim::System,public gz::sim::ISystemConfigure,
  public gz::sim::ISystemPreUpdate {
  std::ofstream log_;
  std::map<std::string,gz::sim::Entity> links_,joints_;
  double mass_{.3},push_{2.},down_{1.};
  size_t samples_{0};
public:
  void Configure(const gz::sim::Entity &,const std::shared_ptr<const sdf::Element> & s,
    gz::sim::EntityComponentManager &,gz::sim::EventManager &) override {
    log_.open(s->Get<std::string>("output"),std::ios::out|std::ios::trunc);
    if(!log_)throw std::runtime_error("Cannot open force-reference output");
    mass_=s->Get<double>("mass");push_=s->Get<double>("push");down_=s->Get<double>("down");
  }
  void PreUpdate(const gz::sim::UpdateInfo & info,gz::sim::EntityComponentManager & ecm) override {
    if(info.paused)return;
    if(links_.empty()) {
      ecm.Each<gz::sim::components::Name,gz::sim::components::Link>(
        [&](const auto & e,const auto * name,const auto *) {
          if(name->Data()=="load_body" || name->Data()=="free_body" || name->Data()=="drop_body" || name->Data().rfind("wrench_body",0)==0) {
            links_[name->Data()]=e;gz::sim::Link link(e);
            link.EnableVelocityChecks(ecm);link.EnableAccelerationChecks(ecm);
          }return true;
        });
      ecm.Each<gz::sim::components::Name,gz::sim::components::Joint>(
        [&](const auto & e,const auto * name,const auto *) {
          if(name->Data().rfind("reference_fixed",0)==0) {
            joints_[name->Data()]=e;
            if(!ecm.Component<gz::sim::components::JointTransmittedWrench>(e))
              ecm.CreateComponent(e,gz::sim::components::JointTransmittedWrench());
          }return true;
        });
    }
    const double next=std::chrono::duration<double>(info.simTime).count();
    const double measured=std::max(0.,std::chrono::duration<double>(info.simTime-info.dt).count());
    Json row={{"stamp",measured},{"stamp_kind","completed_previous_physics_step"},
      {"dt",std::chrono::duration<double>(info.dt).count()},{"bodies",Json::object()},
      {"joints",Json::object()},{"contacts",Json::array()}};
    for(const auto & [name,e]:links_) {
      const gz::sim::Link link(e);const auto pose=gz::sim::worldPose(e,ecm);
      auto v=link.WorldLinearVelocity(ecm),a=link.WorldLinearAcceleration(ecm);
      row["bodies"][name]={{"position",vector(pose.Pos())},
        {"quaternion_xyzw",{pose.Rot().X(),pose.Rot().Y(),pose.Rot().Z(),pose.Rot().W()}}};
      if(v)row["bodies"][name]["velocity"]=vector(*v);
      if(a)row["bodies"][name]["acceleration"]=vector(*a);
    }
    for(const auto & [name,e]:joints_) {
      auto w=ecm.Component<gz::sim::components::JointTransmittedWrench>(e);
      if(w)row["joints"][name]=wrench(w->Data());
    }
    ecm.Each<gz::sim::components::ContactSensorData>(
      [&](const auto & e,const auto * data) {
        auto name=ecm.Component<gz::sim::components::Name>(e);
        for(const auto & c:data->Data().contact()) {
          Json points=Json::array();
          for(int i=0;i<c.position_size();++i) {
            Json p={{"position_world",vector(c.position(i))},{"wrench_present",i<c.wrench_size()}};
            if(i<c.normal_size())p["normal_world"]=vector(c.normal(i));
            if(i<c.depth_size())p["depth_m"]=c.depth(i);
            if(i<c.wrench_size()) {
              p["body1"]=wrench(c.wrench(i).body_1_wrench());
              p["body2"]=wrench(c.wrench(i).body_2_wrench());
            }points.push_back(p);
          }
          row["contacts"].push_back({{"sensor",name ? name->Data():""},
            {"collision1",gz::sim::scopedName(c.collision1().id(),ecm,"::")},
            {"collision2",gz::sim::scopedName(c.collision2().id(),ecm,"::")},
            {"points",points}});
        }return true;
      });
    // Force is commanded every physics step; never reset poses/velocities.
    // Log the completed result first, apply the next step's known excitation.
    const double push=next>=1. && next<2. ? push_:0.;
    const double down=next>=2. ? down_:0.;
    for(const auto & [name,e]:links_) {
      gz::msgs::Wrench w;
      if(name=="free_body") {w.mutable_force()->set_x(push);w.mutable_force()->set_z(mass_*9.81);}
      if(name=="load_body") {w.mutable_force()->set_x(push);w.mutable_force()->set_z(-down);}
      if(name.rfind("wrench_body",0)==0)w.mutable_force()->set_z(-down);
      auto cmd=ecm.Component<gz::sim::components::ExternalWorldWrenchCmd>(e);
      if(cmd)cmd->Data()=w;else ecm.CreateComponent(e,gz::sim::components::ExternalWorldWrenchCmd(w));
    }
    row["completed_external_push_n"]=(measured>=1. && measured<2.) ? push_:0.;
    row["completed_external_down_n"]=measured>=2. ? down_:0.;
    log_<<row.dump()<<'\n';if(++samples_%100==0)log_.flush();
  }
};
}
GZ_ADD_PLUGIN(uwa_cell_tasks::ForceProbe,gz::sim::System,gz::sim::ISystemConfigure,gz::sim::ISystemPreUpdate)
