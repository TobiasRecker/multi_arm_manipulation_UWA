cmake_minimum_required(VERSION 3.16)
project(uwa_cell_calibration_msgs)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "action/RunCalibration.action" "srv/PrepareCalibration.srv" "srv/ApplyCalibration.srv")
ament_export_dependencies(rosidl_default_runtime)
ament_package()
