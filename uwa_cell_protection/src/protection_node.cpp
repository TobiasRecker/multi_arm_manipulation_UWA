#include "uwa_cell_protection/collision_core.hpp"
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <map>
#include <mutex>
#include <set>
#include <thread>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <std_msgs/msg/string.hpp>
#include <std_srvs/srv/trigger.hpp>
#include <controller_manager_msgs/srv/list_controllers.hpp>
#include <controller_manager_msgs/srv/switch_controller.hpp>
#include <ur_client_library/rtde/rtde_client.h>

namespace uwa_cell_protection
{
using Trigger = std_srvs::srv::Trigger;
using List = controller_manager_msgs::srv::ListControllers;
using Switch = controller_manager_msgs::srv::SwitchController;
using String = std_msgs::msg::String;
namespace
{
double monotonic()
{
  return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}
bool finite(const std::vector<double> & values)
{
  return values.size() == 6 && std::all_of(values.begin(), values.end(), [](double v) { return std::isfinite(v); });
}
std::string arm_of(std::string link)
{
  if (link.rfind("calibrated/", 0) == 0) link.erase(0, 11);
  for (const auto * arm : arm_ids)
    if (link.rfind(std::string(arm) + "_", 0) == 0) return arm;
  return "";
}
struct Sample
{
  std::vector<double> q, v;
  double stamp = 0., received = -1., source = -1., offset = 0.;
};
struct Arm
{
  std::string id, ip, ns, controller;
  std::vector<std::string> joints;
  rclcpp::Publisher<String>::SharedPtr command;
  rclcpp::Subscription<String>::SharedPtr ack_subscription;
  rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr mock_subscription;
  rclcpp::Client<List>::SharedPtr list;
  rclcpp::Client<Switch>::SharedPtr switch_controller;
  Json ack = Json::object();
  std::string error;
  bool fallback_hold = false;
};
}
class ProtectionNode : public rclcpp::Node
{
  std::string mode_, signature_;
  Json config_, collisions_ = Json::array(), pair_status_ = Json::array();
  std::unique_ptr<CollisionCore> core_;
  std::map<std::string, Arm> arms_;
  std::map<std::string, Sample> samples_;
  std::map<std::string, std::string> source_errors_;
  std::mutex sample_mutex_;
  std::atomic<bool> done_{false};
  std::vector<std::thread> readers_;
  std::set<std::string> available_;
  std::map<std::string, double> recovery_baselines_;
  std::string recovery_sha_;
  bool paused_ = false;
  std::string reason_ = "RUNNING";
  uint64_t generation_ = 0;
  double timeout_ = .2, rate_ = 20.;
  rclcpp::Publisher<String>::SharedPtr status_pub_, state_pub_;
  rclcpp::Service<Trigger>::SharedPtr pause_service_, resume_service_, status_service_, recovery_service_;
  rclcpp::TimerBase::SharedPtr timer_;

public:
  ProtectionNode() : Node("protection", "/uwa_cell")
  {
    mode_ = declare_parameter<std::string>("mode", "mock");
    const auto file = declare_parameter<std::string>("model_config", "");
    declare_parameter<std::string>("recovery_plan_path", "");
    const char * domain_text = std::getenv("ROS_DOMAIN_ID");
    const std::string domain = domain_text ? domain_text : "0";
    if ((mode_ != "mock" && mode_ != "hardware") ||
        (mode_ == "mock" && domain != "67") || (mode_ == "hardware" && domain != "66"))
      throw std::runtime_error("Explicit mock/Domain67 or hardware/Domain66 required");
    config_ = load_config(file);
    signature_ = config_.at("model_signature");
    rate_ = config_.value("rate_hz", 20.);
    timeout_ = config_.value("state_timeout_s", .2);
    if (rate_ != 20. || timeout_ != .2)
      throw std::runtime_error("Approved profile uses 20 Hz and 0.2 s warning age");
    core_ = std::make_unique<CollisionCore>(config_, std::filesystem::path(file).parent_path().string());
    const auto qos = rclcpp::QoS(1).reliable().transient_local();
    status_pub_ = create_publisher<String>("/uwa_cell/protection/status", qos);
    state_pub_ = create_publisher<String>("/uwa_cell/protection/state", qos);
    for (const auto * rid : arm_ids) {
      auto & a = arms_[rid];
      const auto & entry = config_.at("arms").at(rid);
      a.id = rid; a.ns = entry.at("namespace");
      a.ip = entry.at("ip");
      a.joints = entry.at("joint_names").get<std::vector<std::string>>();
      a.controller = entry.value("controller", mode_ == "hardware" ?
          "scaled_joint_trajectory_controller" : "joint_trajectory_controller");
      a.command = create_publisher<String>(a.ns + "/" + a.controller + "/pause_command", qos);
      a.ack_subscription = create_subscription<String>(a.ns + "/" + a.controller + "/pause_status", qos,
        [this, rid](const String & message) {
          try {
            auto value = Json::parse(message.data);
            if (value.is_object() && value.contains("generation") && value["generation"].is_number_unsigned() &&
                value.contains("paused") && value["paused"].is_boolean() &&
                value.contains("factor") && value["factor"].is_number() &&
                value.contains("resumable") && value["resumable"].is_boolean()) arms_.at(rid).ack = value;
          } catch (const Json::exception &) { arms_.at(rid).error = "Invalid pause acknowledgement"; }
        });
      a.list = create_client<List>(a.ns + "/controller_manager/list_controllers");
      a.switch_controller = create_client<Switch>(a.ns + "/controller_manager/switch_controller");
      if (mode_ == "mock")
        a.mock_subscription = create_subscription<sensor_msgs::msg::JointState>(a.ns + "/joint_states",
          rclcpp::SensorDataQoS(), [this, rid](const sensor_msgs::msg::JointState & message) {
            auto & arm = arms_.at(rid);
            std::vector<double> q, v;
            for (const auto & joint : arm.joints) {
              auto found = std::find(message.name.begin(), message.name.end(), joint);
              const auto index = static_cast<size_t>(found - message.name.begin());
              if (found == message.name.end() || index >= message.position.size() || index >= message.velocity.size()) return;
              q.push_back(message.position[index]); v.push_back(message.velocity[index]);
            }
            accept(rid, message.header.stamp.sec + message.header.stamp.nanosec * 1e-9, q, v);
          });
    }
    pause_service_ = create_service<Trigger>("/uwa_cell/protection/pause_all",
      [this](const Trigger::Request::SharedPtr, Trigger::Response::SharedPtr response) {
        pause("OPERATOR PAUSE");
        response->success = true; response->message = status().dump();
      });
    resume_service_ = create_service<Trigger>("/uwa_cell/protection/resume_all",
      [this](const Trigger::Request::SharedPtr, Trigger::Response::SharedPtr response) {
        try { evaluate(); } catch (const std::exception & error) {
          available_.clear();
          RCLCPP_WARN(get_logger(), "Collision data unavailable during operator resume: %s", error.what());
        }
        if (!collisions_.empty()) {
          response->success = false;
          auto value = status(); value["command_error"] = "Known collision remains; use a checked withdrawal or new path";
          response->message = value.dump(); return;
        }
        for (const auto & [id, arm] : arms_)
          if (arm.ack.value("generation", uint64_t(0)) == generation_ &&
              arm.ack.contains("resumable") && !arm.ack.value("resumable", true)) {
            response->success = false;
            auto value = status(); value["command_error"] = id + ": previous trajectory cannot be resumed; plan a new path";
            response->message = value.dump(); return;
          }
        if (paused_) { paused_ = false; reason_ = "OPERATOR RESUME"; ++generation_; publish_commands(); }
        response->success = true; response->message = status().dump();
      });
    status_service_ = create_service<Trigger>("/uwa_cell/protection/status",
      [this](const Trigger::Request::SharedPtr, Trigger::Response::SharedPtr response) {
        response->success = true; response->message = status().dump();
      });
    recovery_service_ = create_service<Trigger>("/uwa_cell/protection/begin_recovery",
      [this](const Trigger::Request::SharedPtr, Trigger::Response::SharedPtr response) {
        try {
          begin_recovery(); response->success = true; response->message = status().dump();
        } catch (const std::exception & error) {
          response->success = false;
          auto value = status(); value["command_error"] = error.what(); response->message = value.dump();
        }
      });
    timer_ = create_wall_timer(std::chrono::milliseconds(50), [this] { tick(); });
    if (mode_ == "hardware")
      for (const auto * rid : arm_ids) readers_.emplace_back([this, rid] { read_rtde(rid); });
    RCLCPP_INFO(get_logger(), "Minimal collision protection in %s mode: collision pause only; missing data warns only", mode_.c_str());
  }
  ~ProtectionNode() override
  {
    done_ = true;
    for (auto & reader : readers_) if (reader.joinable()) reader.join();
  }
private:
  void accept(const std::string & id, double stamp, const std::vector<double> & q, const std::vector<double> & v)
  {
    if (!finite(q) || !finite(v) || !std::isfinite(stamp)) return;
    const double now = monotonic();
    std::lock_guard<std::mutex> lock(sample_mutex_);
    auto previous = samples_.find(id);
    if (previous != samples_.end() && stamp == previous->second.stamp) return;
    double offset = now - stamp;
    if (previous != samples_.end() && stamp > previous->second.stamp)
      offset = std::min(offset, previous->second.offset);
    samples_[id] = Sample{q, v, stamp, now, stamp + offset, offset};
    source_errors_.erase(id);
  }
  void read_rtde(const std::string & id)
  {
    const auto ip = arms_.at(id).ip;
    while (!done_) {
      try {
        urcl::comm::INotifier notifier;
        const std::vector<std::string> outputs{"timestamp", "actual_q", "actual_qd"};
        const std::vector<std::string> inputs;  // Output-only: no registers or robot commands.
        urcl::rtde_interface::RTDEClient client(ip, notifier, outputs, inputs, rate_);
        if (!client.init(1, std::chrono::milliseconds(500), 1) || !client.start(true))
          throw std::runtime_error("RTDE output connection unavailable");
        urcl::rtde_interface::DataPackage package(client.getOutputRecipe());
        while (!done_) {
          if (!client.getDataPackage(package, std::chrono::milliseconds(200))) continue;
          double stamp;
          urcl::vector6d_t q, v;
          if (package.getData("timestamp", stamp) && package.getData("actual_q", q) && package.getData("actual_qd", v))
            accept(id, stamp, {q.begin(), q.end()}, {v.begin(), v.end()});
        }
      } catch (const std::exception & error) {
        std::lock_guard<std::mutex> lock(sample_mutex_);
        source_errors_[id] = error.what();
      }
      for (unsigned i = 0; i != 10 && !done_; ++i) std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
  }
  void publish_commands()
  {
    const Json value{{"generation", generation_}, {"paused", paused_}, {"reason", reason_},
                     {"command_time_monotonic_s", monotonic()}};
    String message; message.data = value.dump();
    for (auto & [id, arm] : arms_) arm.command->publish(message);
  }
  void pause(const std::string & reason)
  {
    if (paused_) return;
    paused_ = true; reason_ = reason; ++generation_;
    publish_commands();  // Always before the optional one-shot inventory RPC.
    for (auto & [id, arm] : arms_) inspect_on_pause(id, generation_);
    RCLCPP_WARN(get_logger(), "All-arm software pause requested: %s", reason.c_str());
  }
  void inspect_on_pause(const std::string & id, uint64_t generation)
  {
    auto & arm = arms_.at(id);
    arm.error.clear();
    arm.fallback_hold = false;
    if (!arm.list->service_is_ready()) { arm.error = "Controller inventory unavailable; pause acknowledgement unconfirmed"; return; }
    arm.list->async_send_request(std::make_shared<List::Request>(),
      [this, id, generation](rclcpp::Client<List>::SharedFuture future) {
        if (!paused_ || generation != generation_) return;
        auto & a = arms_.at(id);
        try {
          const auto reply = future.get();
          std::vector<std::string> deactivate;
          bool holding = false;
          for (const auto & controller : reply->controller) {
            if (controller.state != "active") continue;
            if (controller.name == a.controller) { a.fallback_hold = false; return; }
            if (controller.name == "collision_hold_controller") holding = true;
            bool owns_arm = false;
            for (const auto & interface : controller.claimed_interfaces)
              for (const auto & joint : a.joints)
                owns_arm |= interface.rfind(joint + "/", 0) == 0;
            if (owns_arm && controller.name != "collision_hold_controller") deactivate.push_back(controller.name);
          }
          if (holding && deactivate.empty()) { a.fallback_hold = true; return; }
          if (!a.switch_controller->service_is_ready()) { a.error = "Hold switch unavailable"; return; }
          auto request = std::make_shared<Switch::Request>();
          request->activate_controllers = {"collision_hold_controller"};
          request->deactivate_controllers = deactivate;
          request->strictness = Switch::Request::FORCE_AUTO;
          request->activate_asap = true;
          request->timeout.sec = 1;
          a.switch_controller->async_send_request(request,
            [this, id, generation](rclcpp::Client<Switch>::SharedFuture result) {
              if (generation != generation_) return;
              auto & target = arms_.at(id);
              try {
                const auto answer = result.get();
                target.fallback_hold = answer->ok;
                if (!answer->ok) target.error = "Hold switch rejected: " + answer->message;
              } catch (const std::exception & error) { target.error = error.what(); }
            });
        } catch (const std::exception & error) { a.error = error.what(); }
      });
  }
  static std::string pair_key(const Json & entry)
  {
    if (entry.value("kind", "") != "neighbor_margin" || !entry.contains("arms")) return "";
    const auto arms = entry.at("arms").get<std::vector<std::string>>();
    return arms.size() == 2 ? arms[0] + ":" + arms[1] : "";
  }
  void begin_recovery()
  {
    if (!paused_) throw std::runtime_error("Pause all arms before admitting a checked withdrawal");
    evaluate();
    if (available_.size() != 4) throw std::runtime_error("Current four-arm geometry required to check recovery start");
    std::ifstream stream(get_parameter("recovery_plan_path").as_string());
    if (!stream) throw std::runtime_error("Cannot read recovery plan");
    const auto plan = Json::parse(stream);
    if (plan.at("model_signature").get<std::string>() != signature_ ||
        plan.at("reviewed_sha256").get<std::string>().size() != 64 ||
        !plan.contains("trajectories") || !plan.at("trajectories").is_object() || plan.at("trajectories").empty())
      throw std::runtime_error("Recovery requires matching model and bound reviewed trajectories");
    const auto & states = plan.at("states");
    const double tolerance = plan.at("start_tolerance_rad");
    if (!states.is_array() || states.size() < 2 || !std::isfinite(tolerance) || tolerance <= 0.)
      throw std::runtime_error("Recovery needs checked states and existing start tolerance");
    std::map<std::string, Sample> samples;
    { std::lock_guard<std::mutex> lock(sample_mutex_); samples = samples_; }
    const auto start = states.at(0).get<std::map<std::string, double>>();
    for (const auto & [id, arm] : arms_)
      for (size_t i = 0; i != 6; ++i)
        if (!start.count(arm.joints[i]) || !std::isfinite(start.at(arm.joints[i])) ||
            std::abs(start.at(arm.joints[i]) - samples.at(id).q[i]) > tolerance)
          throw std::runtime_error("Recovery start differs from current measured arm positions");
    const auto initial = core_->evaluate(start, available_);
    std::map<std::string, double> baselines, previous;
    for (const auto & conflict : initial.at("collisions")) {
      const auto key = pair_key(conflict);
      if (key.empty()) throw std::runtime_error("Recovery cannot start from an actual FCL model collision");
      baselines[key] = previous[key] = conflict.at("distance_m");
    }
    if (baselines.empty()) throw std::runtime_error("No neighbor margin conflict requires recovery; use an ordinary checked path");
    Json final;
    for (const auto & item : states) {
      const auto result = core_->evaluate(item.get<std::map<std::string, double>>(), available_);
      for (const auto & conflict : result.at("collisions"))
        if (!baselines.count(pair_key(conflict)))
          throw std::runtime_error("Recovery introduces another conflict or FCL contact");
      for (const auto & pair : result.at("pairs")) {
        const auto key = pair_key(pair);
        if (!baselines.count(key)) continue;
        const double gap = pair.at("distance_m");
        if (gap < previous.at(key) - 1e-9)
          throw std::runtime_error("Recovery checked states further approach a conflicting neighbor");
        previous[key] = gap;
      }
      final = result;
    }
    if (!final.at("clear").get<bool>()) throw std::runtime_error("Recovery must end outside every 40 mm neighbor margin");
    recovery_baselines_ = std::move(baselines);
    recovery_sha_ = plan.at("reviewed_sha256");
    collisions_ = Json::array();
    reason_ = "CHECKED RECOVERY READY; OPERATOR RESUME REQUIRED";
    evaluate();
  }
  void evaluate()
  {
    std::map<std::string, Sample> records;
    { std::lock_guard<std::mutex> lock(sample_mutex_); records = samples_; }
    const double now = monotonic();
    available_.clear();
    std::map<std::string, double> positions, velocities;
    Json serialized = Json::object();
    for (const auto & [id, sample] : records) {
      const auto & names = arms_.at(id).joints;
      for (size_t i = 0; i != 6; ++i) { positions[names[i]] = sample.q[i]; velocities[names[i]] = sample.v[i]; }
      serialized[id] = {{"q", sample.q}, {"v", sample.v}, {"device_timestamp", sample.stamp},
                        {"received_monotonic_s", sample.received}, {"source_monotonic_s", sample.source}};
      if (now - sample.received <= timeout_ && now - sample.source <= timeout_) available_.insert(id);
    }
    auto value = core_->evaluate(positions, available_);
    Json current = Json::array();
    for (const auto & conflict : value.at("collisions")) {
      const auto key = pair_key(conflict);
      auto exception = recovery_baselines_.find(key);
      if (exception != recovery_baselines_.end() &&
          conflict.at("distance_m").get<double>() >= exception->second - 1e-9) continue;
      current.push_back(conflict);
    }
    bool recovery_clear = !recovery_baselines_.empty();
    for (const auto & [key, baseline] : recovery_baselines_) {
      bool pair_clear = false;
      for (const auto & pair : value.at("pairs"))
        if (pair_key(pair) == key && pair.at("distance_m").get<double>() > .04) pair_clear = true;
      recovery_clear &= pair_clear;
    }
    if (recovery_clear) { recovery_baselines_.clear(); recovery_sha_.clear(); }
    // Missing data does not add a stop and cannot erase a previously observed
    // unresolved collision involving that missing arm.
    for (const auto & conflict : collisions_) {
      bool unknown = false;
      if (!conflict.contains("links") || conflict.at("links").empty()) unknown = available_.size() != 4;
      else for (const auto & link : conflict.at("links")) {
        const auto arm = arm_of(link.get<std::string>());
        if (!arm.empty() && !available_.count(arm)) unknown = true;
      }
      if (unknown && std::find(current.begin(), current.end(), conflict) == current.end()) current.push_back(conflict);
    }
    collisions_ = std::move(current); pair_status_ = value.at("pairs");
    if (!collisions_.empty()) pause("COLLISION");
    String message;
    message.data = Json{{"mode", mode_}, {"positions", positions}, {"velocities", velocities},
                        {"records", serialized}, {"model_signature", signature_},
                        {"evaluated_monotonic_s", now}}.dump();
    state_pub_->publish(message);
  }
  Json status()
  {
    Json states = Json::object(), unavailable = Json::array(), warnings = Json::array();
    bool all_confirmed = true, all_zero = true;
    for (const auto & [id, arm] : arms_) {
      const bool confirmed = generation_ != 0 && arm.ack.value("generation", uint64_t(0)) == generation_ &&
        arm.ack.value("paused", !paused_) == paused_;
      Json entry = arm.ack;
      entry["confirmed"] = confirmed || (paused_ && arm.fallback_hold);
      entry["controller"] = arm.fallback_hold ? "collision_hold_controller" : arm.controller;
      entry["error"] = arm.error;
      entry["resumable"] = arm.fallback_hold ? false : arm.ack.value("resumable", true);
      states[id] = entry;
      all_confirmed &= entry.at("confirmed").get<bool>();
      all_zero &= arm.fallback_hold || (confirmed && arm.ack.value("factor", 1.) == 0.);
      if (!available_.count(id)) unavailable.push_back(id);
      if (!arm.error.empty()) warnings.push_back(id + ": " + arm.error);
    }
    if (!unavailable.empty()) warnings.push_back("COLLISION DATA UNAVAILABLE: affected body pairs are not monitored; motion continues");
    if (generation_ && !all_confirmed) warnings.push_back("SOFTWARE PAUSE/RESUME ACKNOWLEDGEMENT UNCONFIRMED");
    return {{"mode", mode_}, {"paused", paused_}, {"pausing", paused_ && !all_zero},
            {"state", paused_ ? (all_zero ? "PAUSED" : "PAUSE REQUESTED") : "RUNNING"},
            {"reason", reason_}, {"generation", generation_}, {"collision_data_available", unavailable.empty()},
            {"unavailable_arms", unavailable}, {"known_collisions", collisions_}, {"pairs", pair_status_},
            {"warnings", warnings}, {"arms", states}, {"model_signature", signature_},
            {"recovery_active", !recovery_baselines_.empty()}, {"recovery_reviewed_sha256", recovery_sha_},
            {"evaluated_monotonic_s", monotonic()}};
  }
  void tick()
  {
    try { evaluate(); }
    catch (const std::exception & error) {
      available_.clear();
      RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 5000, "Collision data unavailable; no automatic pause: %s", error.what());
    }
    String message; message.data = status().dump(); status_pub_->publish(message);
  }
};
}  // namespace uwa_cell_protection
int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  try { rclcpp::spin(std::make_shared<uwa_cell_protection::ProtectionNode>()); }
  catch (const std::exception & error) {
    std::fprintf(stderr, "Protection startup failed: %s\n", error.what());
    rclcpp::shutdown(); return 1;
  }
  rclcpp::shutdown();
}
