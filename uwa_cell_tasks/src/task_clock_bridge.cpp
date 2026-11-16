// Private, native simulation clock. No Python GIL or image/contact work on
// the timing path. Publish at100Hz simulation time; do not fabricate time.
#include <atomic>
#include <mutex>
#include <string>
#include <gz/msgs/clock.pb.h>
#include <gz/transport/Node.hh>
#include <rclcpp/rclcpp.hpp>
#include <rosgraph_msgs/msg/clock.hpp>

class TaskClock : public rclcpp::Node
{
  gz::transport::Node transport_;
  rclcpp::Publisher<rosgraph_msgs::msg::Clock>::SharedPtr publisher_;
  std::mutex mutex_;
  std::string topic_;
  bool closing_{false};
  int64_t last_{-10000000};
public:
  TaskClock():Node("task_clock_bridge")
  {
    if(std::string(get_namespace()).rfind("/uwa_grasp_",0)!=0)
      throw std::runtime_error("Private /uwa_grasp_* namespace required");
    const auto world=declare_parameter<std::string>("world","uwa_grasp_lab");
    topic_="/world/"+world+"/clock";
    publisher_=create_publisher<rosgraph_msgs::msg::Clock>("clock",rclcpp::QoS(1).best_effort());
    if(!transport_.Subscribe(topic_,&TaskClock::receive,this))throw std::runtime_error("Clock subscription failed");
    RCLCPP_INFO(get_logger(),"PRIVATE CLOCK READY: %s,100Hz simulation-time publication",topic_.c_str());
  }
  void receive(const gz::msgs::Clock & message)
  {
    std::lock_guard<std::mutex> lock(mutex_);
    if(closing_ || !rclcpp::ok())return;
    const int64_t stamp=message.sim().sec()*1000000000LL+message.sim().nsec();
    if(stamp>=last_ && stamp-last_<10000000)return;
    last_=stamp;rosgraph_msgs::msg::Clock out;
    out.clock.sec=message.sim().sec();out.clock.nanosec=message.sim().nsec();
    publisher_->publish(out);
  }
  ~TaskClock() override
  {
    {std::lock_guard<std::mutex> lock(mutex_);closing_=true;}
    transport_.Unsubscribe(topic_);
  }
};

int main(int argc,char ** argv)
{
  rclcpp::init(argc,argv);
  try {rclcpp::spin(std::make_shared<TaskClock>());}
  catch(const std::exception & error) {RCLCPP_ERROR(rclcpp::get_logger("task_clock_bridge"),"%s",error.what());rclcpp::shutdown();return 1;}
  rclcpp::shutdown();return 0;
}
