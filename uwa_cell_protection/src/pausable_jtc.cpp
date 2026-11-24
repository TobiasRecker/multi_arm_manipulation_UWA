// Copyright 2026 UWA contributors. SPDX-License-Identifier: Apache-2.0
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cctype>
#include <memory>
#include <mutex>
#include <string>

#include <joint_trajectory_controller/joint_trajectory_controller.hpp>
#include <action_msgs/msg/goal_status_array.hpp>
#include <nlohmann/json.hpp>
#include <pluginlib/class_list_macros.hpp>
#include <rclcpp_action/create_server.hpp>
#include <std_msgs/msg/string.hpp>

#include "uwa_cell_protection/pause_ramp.hpp"

namespace uwa_cell_protection
{
using Json = nlohmann::json;

class PausableJointTrajectoryController final
  : public joint_trajectory_controller::JointTrajectoryController
{
  using Base = joint_trajectory_controller::JointTrajectoryController;
  using GoalHandle = rclcpp_action::ServerGoalHandle<FollowJTrajAction>;
  std::mutex admission_;
  bool have_command_{false};
  uint64_t generation_{0};
  std::string reason_;
  std::atomic<bool> requested_pause_{false};
  std::atomic<double> factor_report_{1.0};
  std::atomic<double> phase_report_{0.0};
  std::atomic<bool> active_report_{false};
  std::atomic<bool> deactivated_with_goal_{false};
  std::shared_ptr<GoalHandle> retained_goal_;
  std::string retained_uuid_;
  std::string active_uuid_;
  Json recovery_trajectory_;
  std::string recovery_sha_;
  std::string recovery_reserved_uuid_;
  bool recovery_consumed_{true};
  std::string active_recovery_sha_;
  std::atomic<bool> active_recovery_valid_{false};
  double factor_{1.0};
  double acceleration_{0.2};
  double normal_velocity_{0.1};
  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr pause_subscription_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr pause_publisher_;
  rclcpp::TimerBase::SharedPtr status_timer_;
  rclcpp::Subscription<action_msgs::msg::GoalStatusArray>::SharedPtr action_status_;

  bool rejects_new_motion() const
  {
    return requested_pause_.load(std::memory_order_acquire) || factor_report_.load() < 1.0 - 1e-9;
  }

  bool matches_recovery(const FollowJTrajAction::Goal & goal) const
  {
    if (!requested_pause_.load() || recovery_consumed_ || !recovery_trajectory_.is_object()) {
      return false;
    }
    try {
      const auto & trajectory = goal.trajectory;
      if (trajectory.joint_names != recovery_trajectory_.at("joint_names").get<std::vector<std::string>>() ||
        trajectory.points.size() != recovery_trajectory_.at("points").size()) {return false;}
      for (size_t i = 0; i < trajectory.points.size(); ++i) {
        const auto & actual = trajectory.points[i];
        const auto & expected = recovery_trajectory_.at("points").at(i);
        if (actual.positions != expected.at("positions").get<std::vector<double>>() ||
          actual.velocities != expected.value("velocities", std::vector<double>{}) ||
          actual.accelerations != expected.value("accelerations", std::vector<double>{}) ||
          !actual.effort.empty()) {return false;}
        const double seconds = expected.at("time").get<double>();
        if (!std::isfinite(seconds) || seconds < 0.0) {return false;}
        const int64_t expected_ns = std::llround(seconds * 1e9);
        const int64_t actual_ns = int64_t(actual.time_from_start.sec) * 1000000000LL +
          actual.time_from_start.nanosec;
        if (std::abs(actual_ns - expected_ns) > 1) {return false;}
      }
      return true;
    } catch (const std::exception &) {return false;}
  }

  void command(const std_msgs::msg::String & message)
  {
    try {
      const auto value = Json::parse(message.data);
      if (!value.is_object() || !value.contains("generation") ||
        !value["generation"].is_number_unsigned() || !value.contains("paused") ||
        !value["paused"].is_boolean()) {
        throw std::invalid_argument("generation must be unsigned and paused must be boolean");
      }
      const auto generation = value.at("generation").get<uint64_t>();
      const bool paused = value.at("paused").get<bool>();
      const auto reason = value.value("reason", std::string{});
      Json recovery;
      std::string recovery_sha;
      if (paused && value.contains("recovery_trajectory")) {
        recovery_sha = value.value("recovery_reviewed_sha256", std::string{});
        if (recovery_sha.size() != 64 || !std::all_of(recovery_sha.begin(), recovery_sha.end(),
          [](unsigned char ch) {return std::isxdigit(ch);})) {
          throw std::invalid_argument("Recovery needs its reviewed SHA-256");
        }
        recovery = value.at("recovery_trajectory");
        if (!recovery.is_object()) {throw std::invalid_argument("Recovery trajectory must be an object");}
      }
      std::lock_guard<std::mutex> lock(admission_);
      if (have_command_ && generation <= generation_) {return;}
      if (paused && !requested_pause_.load()) {
        const auto active = *rt_active_goal_.readFromNonRT();
        retained_goal_ = active ? active->gh_ : nullptr;
        retained_uuid_ = retained_goal_ ? rclcpp_action::to_string(retained_goal_->get_goal_id()) : "";
        deactivated_with_goal_ = false;
      }
      generation_ = generation;
      have_command_ = true;
      reason_ = reason;
      if (paused) {
        recovery_reserved_uuid_.clear();
        recovery_trajectory_ = nullptr;
        recovery_sha_.clear();
        recovery_consumed_ = true;
        if (!recovery.is_null()) {
          recovery_trajectory_ = std::move(recovery);
          recovery_sha_ = std::move(recovery_sha);
          recovery_consumed_ = false;
        }
      }
      requested_pause_.store(paused, std::memory_order_release);
    } catch (const std::exception & error) {
      RCLCPP_WARN(get_node()->get_logger(), "Ignored invalid pause command: %s", error.what());
    }
  }

  void publish_status()
  {
    std::lock_guard<std::mutex> lock(admission_);
    bool resumable = !deactivated_with_goal_.load();
    Json value{{"generation", generation_}, {"paused", requested_pause_.load()},
      {"factor", factor_report_.load()}, {"resumable", resumable},
      {"phase_time_s", phase_report_.load()}, {"action_active", active_report_.load()},
      {"reason", reason_}};
    value["recovery_authorized"] = !recovery_consumed_;
    value["active_recovery_sha256"] = active_report_.load() && active_recovery_valid_.load() ?
      active_recovery_sha_ : "";
    if (active_report_.load()) {value["active_goal"] = active_uuid_;}
    std_msgs::msg::String message;
    message.data = value.dump();
    pause_publisher_->publish(message);
  }

public:
  controller_interface::CallbackReturn on_init() override
  {
    if (Base::on_init() != controller_interface::CallbackReturn::SUCCESS) {
      return controller_interface::CallbackReturn::ERROR;
    }
    acceleration_ = auto_declare<double>("pause_joint_acceleration", 0.2);
    normal_velocity_ = auto_declare<double>("pause_joint_velocity", 0.1);
    if (!std::isfinite(acceleration_) || acceleration_ <= 0.0 ||
      !std::isfinite(normal_velocity_) || normal_velocity_ <= 0.0) {
      return controller_interface::CallbackReturn::ERROR;
    }
    return controller_interface::CallbackReturn::SUCCESS;
  }

  controller_interface::CallbackReturn on_configure(const rclcpp_lifecycle::State & state) override
  {
    if (Base::on_configure(state) != controller_interface::CallbackReturn::SUCCESS) {
      return controller_interface::CallbackReturn::ERROR;
    }
    if (!has_position_command_interface_ || has_velocity_command_interface_ ||
      has_acceleration_command_interface_ || has_effort_command_interface_ ||
      params_.allow_trajectory_replacement) {
      RCLCPP_ERROR(get_node()->get_logger(),
        "Pausable JTC requires position-only commands and trajectory replacement disabled");
      return controller_interface::CallbackReturn::ERROR;
    }
    // Rebind the nonvirtual base callbacks. A pause never cancels/preempts the
    // existing goal; commands submitted during the pause cannot replace it.
    action_server_.reset();
    action_server_ = rclcpp_action::create_server<FollowJTrajAction>(
      get_node()->get_node_base_interface(), get_node()->get_node_clock_interface(),
      get_node()->get_node_logging_interface(), get_node()->get_node_waitables_interface(),
      std::string(get_node()->get_name()) + "/follow_joint_trajectory",
      [this](const rclcpp_action::GoalUUID & uuid,
      std::shared_ptr<const FollowJTrajAction::Goal> goal) {
        std::lock_guard<std::mutex> lock(admission_);
        if (rejects_new_motion()) {
          if (!recovery_reserved_uuid_.empty() || !matches_recovery(*goal)) {
            return rclcpp_action::GoalResponse::REJECT;
          }
          const auto response = Base::goal_received_callback(uuid, goal);
          if (response != rclcpp_action::GoalResponse::REJECT) {
            recovery_reserved_uuid_ = rclcpp_action::to_string(uuid);
          }
          return response;
        }
        return Base::goal_received_callback(uuid, goal);
      },
      [this](std::shared_ptr<GoalHandle> goal) {
        std::lock_guard<std::mutex> lock(admission_);
        if (rclcpp_action::to_string(goal->get_goal_id()) == active_uuid_) {
          if (requested_pause_.load() && active_report_.load()) {deactivated_with_goal_ = true;}
          active_recovery_valid_ = false;
        }
        return Base::goal_cancelled_callback(goal);
      },
      [this](std::shared_ptr<GoalHandle> goal) {
        std::lock_guard<std::mutex> lock(admission_);
        const auto uuid = rclcpp_action::to_string(goal->get_goal_id());
        const bool recovery = uuid == recovery_reserved_uuid_ && matches_recovery(*goal->get_goal());
        if (rejects_new_motion() && !recovery) {
          auto result = std::make_shared<FollowJTrajAction::Result>();
          result->error_code = FollowJTrajAction::Result::INVALID_GOAL;
          result->error_string = "Software pause received before goal admission completed";
          goal->abort(result);
          return;
        }
        active_uuid_ = uuid;
        // A newly reviewed normal task owns its own lifecycle. A canceled or
        // aborted previous task must not keep its old resumability diagnosis.
        deactivated_with_goal_ = false;
        if (recovery) {
          recovery_consumed_ = true;
          recovery_reserved_uuid_.clear();
          retained_goal_ = goal;
          retained_uuid_ = uuid;
          active_recovery_sha_ = recovery_sha_;
          active_recovery_valid_ = true;
        } else {
          retained_goal_.reset();
          retained_uuid_.clear();
          active_recovery_sha_.clear();
          active_recovery_valid_ = false;
        }
        Base::goal_accepted_callback(goal);
      });
    joint_command_subscriber_.reset();
    joint_command_subscriber_ = get_node()->create_subscription<trajectory_msgs::msg::JointTrajectory>(
      "~/joint_trajectory", rclcpp::SystemDefaultsQoS(),
      [this](const trajectory_msgs::msg::JointTrajectory::SharedPtr message) {
        std::lock_guard<std::mutex> lock(admission_);
        if (!rejects_new_motion()) {Base::topic_callback(message);}
      });
    const auto qos = rclcpp::QoS(1).reliable().transient_local();
    pause_subscription_ = get_node()->create_subscription<std_msgs::msg::String>(
      "~/pause_command", qos, [this](const std_msgs::msg::String & message) {command(message);});
    pause_publisher_ = get_node()->create_publisher<std_msgs::msg::String>("~/pause_status", qos);
    action_status_ = get_node()->create_subscription<action_msgs::msg::GoalStatusArray>(
      "~/follow_joint_trajectory/_action/status", qos,
      [this](const action_msgs::msg::GoalStatusArray & message) {
        std::lock_guard<std::mutex> lock(admission_);
        for (const auto & entry : message.status_list) {
          if (rclcpp_action::to_string(entry.goal_info.goal_id.uuid) == retained_uuid_ &&
            (entry.status == action_msgs::msg::GoalStatus::STATUS_ABORTED ||
            entry.status == action_msgs::msg::GoalStatus::STATUS_CANCELED)) {
            deactivated_with_goal_ = true;
            active_recovery_valid_ = false;
          }
        }
      });
    status_timer_ = get_node()->create_wall_timer(std::chrono::milliseconds(100),
      [this]() {publish_status();});
    return controller_interface::CallbackReturn::SUCCESS;
  }

  controller_interface::CallbackReturn on_activate(const rclcpp_lifecycle::State & state) override
  {
    factor_ = requested_pause_.load() ? 0.0 : 1.0;
    factor_report_ = factor_;
    active_report_ = false;
    return Base::on_activate(state);
  }

  controller_interface::CallbackReturn on_deactivate(const rclcpp_lifecycle::State & state) override
  {
    if (requested_pause_.load() && active_report_.load()) {deactivated_with_goal_ = true;}
    active_recovery_valid_ = false;
    active_report_ = false;
    return Base::on_deactivate(state);
  }

  controller_interface::return_type update(
    const rclcpp::Time & time, const rclcpp::Duration & period) override
  {
    const bool paused = requested_pause_.load(std::memory_order_acquire);
    double previous = factor_;
    const auto incoming = *new_trajectory_msg_.readFromRT();
    const auto current = current_trajectory_ ? current_trajectory_->get_trajectory_msg() : nullptr;
    const bool future_incoming = incoming && incoming != current && !is_internal_hold(incoming) &&
      rclcpp::Time(incoming->header.stamp, time.get_clock_type()) > time;
    const bool before_start = current && !is_internal_hold(current) &&
      current_trajectory_->is_sampled_already() &&
      traj_time_ < current_trajectory_->time_from_start();
    if (paused && (future_incoming || before_start)) {
      // No moving segment has started. Freeze its remaining start delay too.
      factor_ = previous = 0.0;
    } else {
      factor_ = next_pause_factor(factor_, paused, period.seconds(), acceleration_, normal_velocity_,
        command_next_.velocities, command_next_.accelerations);
    }
    // The public period parameter is JTC6.9.0's trajectory-clock increment.
    // The base subsequently multiplies it by the native UR scaling state.
    // Never overwrite scaling_factor_: it belongs to the hardware layer.
    // Keep JTC's fixed native lookahead. Shrinking it with the pause factor
    // would move the sampled point backwards near the end of the ramp. Once
    // virtual time is frozen, this same future point remains a constant hold.
    const auto result = Base::update(time, period * ((previous + factor_) * 0.5));
    factor_report_.store(factor_);
    const auto active = *rt_active_goal_.readFromRT();
    active_report_.store(static_cast<bool>(active));
    phase_report_.store(rclcpp::Duration(state_desired_.time_from_start).seconds());
    return result;
  }
};
}  // namespace uwa_cell_protection

PLUGINLIB_EXPORT_CLASS(uwa_cell_protection::PausableJointTrajectoryController,
  controller_interface::ControllerInterface)
