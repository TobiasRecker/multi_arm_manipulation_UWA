#include <string>
#include <unordered_set>

#include <gz/plugin/Register.hh>
#include <gz/sim/EventManager.hh>
#include <gz/sim/System.hh>
#include <gz/sim/components/Collision.hh>
#include <gz/sim/components/Model.hh>
#include <gz/sim/components/Name.hh>
#include <gz/sim/physics/Events.hh>

namespace uwa_cell_tasks
{
class GripFriction : public gz::sim::System,
                     public gz::sim::ISystemConfigure,
                     public gz::sim::ISystemPreUpdate
{
  using Entity = gz::sim::Entity;
  using Contact = gz::sim::events::CollectContactSurfaceProperties;

public:
  void Configure(const Entity & model, const std::shared_ptr<const sdf::Element> & sdf,
                 gz::sim::EntityComponentManager &, gz::sim::EventManager & events) override
  {
    model_ = model;
    coefficient_ = sdf->Get<double>("coefficient");
    object_model_ = sdf->Get<std::string>("object_model", "uwa_grasp_carton").first;
    connection_ = events.Connect<Contact>(
      [this](const Entity & first, const Entity & second, const auto &, const auto &,
             const auto &, const auto &, size_t, auto & surface) {
        if ((pads_.count(first) && object_collisions_.count(second)) ||
            (pads_.count(second) && object_collisions_.count(first))) {
          surface.frictionCoeff = coefficient_;
          surface.secondaryFrictionCoeff = coefficient_;
        }
      });
  }

  void PreUpdate(const gz::sim::UpdateInfo &, gz::sim::EntityComponentManager & ecm) override
  {
    namespace c = gz::sim::components;
    if (pads_.size() == 4 && !object_collisions_.empty() && ecm.HasEntity(object_))
      return;
    const auto object = ecm.EntityByComponents(c::Model(), c::Name(object_model_));
    if (object != object_) {
      object_ = object;
      object_collisions_.clear();
    }
    ecm.Each<c::Collision, c::Name>(
      [&](const Entity & collision, const c::Collision *, const c::Name * name) {
        const auto parent_model = ecm.ParentEntity(ecm.ParentEntity(collision));
        if (parent_model == object_ && object_ != gz::sim::kNullEntity)
          object_collisions_.insert(collision);
        if (parent_model != model_ || !IsGripPad(name->Data()))
          return true;
        if (pads_.insert(collision).second)
          ecm.CreateComponent(collision, c::EnableContactSurfaceCustomization(true));
        return true;
      });
  }

private:
  static bool IsGripPad(const std::string & name)
  {
    // SDFormat includes the original pad link name in each lumped collision.
    return name.find("_finger_tip_pad_link_collision") != std::string::npos &&
      (name.find("right_front_robotiq_85_") != std::string::npos ||
       name.find("right_rear_robotiq_85_") != std::string::npos);
  }

  double coefficient_{};
  std::string object_model_;
  Entity model_{gz::sim::kNullEntity};
  Entity object_{gz::sim::kNullEntity};
  std::unordered_set<Entity> pads_;
  std::unordered_set<Entity> object_collisions_;
  gz::common::ConnectionPtr connection_;
};
}  // namespace uwa_cell_tasks

GZ_ADD_PLUGIN(uwa_cell_tasks::GripFriction, gz::sim::System,
              gz::sim::ISystemConfigure, gz::sim::ISystemPreUpdate)
