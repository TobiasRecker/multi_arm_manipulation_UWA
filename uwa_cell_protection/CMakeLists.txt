cmake_minimum_required(VERSION 3.16)
project(uwa_cell_protection)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(std_msgs REQUIRED)
find_package(std_srvs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(controller_manager_msgs REQUIRED)
find_package(controller_interface REQUIRED)
find_package(action_msgs REQUIRED)
find_package(joint_trajectory_controller 6.9.0 EXACT REQUIRED)
find_package(pluginlib REQUIRED)
find_package(realtime_tools REQUIRED)
find_package(moveit_core REQUIRED)
find_package(moveit_ros_planning REQUIRED)
find_package(urdf REQUIRED)
find_package(srdfdom REQUIRED)
find_package(ur_client_library REQUIRED)
find_package(nlohmann_json REQUIRED)
find_package(Threads REQUIRED)
find_package(Python3 COMPONENTS Interpreter REQUIRED)

add_library(collision_core src/collision_core.cpp)
target_include_directories(collision_core PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
target_link_libraries(collision_core PUBLIC ${moveit_core_TARGETS} ${moveit_ros_planning_TARGETS}
  ${urdf_TARGETS} ${srdfdom_TARGETS} nlohmann_json::nlohmann_json)
add_executable(protection_node src/protection_node.cpp)
target_link_libraries(protection_node collision_core ${rclcpp_TARGETS} ${std_msgs_TARGETS}
  ${std_srvs_TARGETS} ${sensor_msgs_TARGETS} ${controller_manager_msgs_TARGETS}
  ur_client_library::urcl Threads::Threads)
add_executable(collision_replay src/collision_replay.cpp)
target_link_libraries(collision_replay collision_core)

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/src/pausable_jtc.cpp")
  add_library(pausable_jtc SHARED src/pausable_jtc.cpp)
  target_include_directories(pausable_jtc PRIVATE include)
  target_link_libraries(pausable_jtc ${joint_trajectory_controller_TARGETS}
    ${controller_interface_TARGETS} ${pluginlib_TARGETS} ${rclcpp_TARGETS}
    ${rclcpp_action_TARGETS} ${std_msgs_TARGETS} ${realtime_tools_TARGETS}
    ${action_msgs_TARGETS} nlohmann_json::nlohmann_json)
  pluginlib_export_plugin_description_file(controller_interface controllers.xml)
  install(TARGETS pausable_jtc LIBRARY DESTINATION lib)
endif()
install(TARGETS collision_core protection_node collision_replay
  ARCHIVE DESTINATION lib LIBRARY DESTINATION lib RUNTIME DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include/ DESTINATION include)
if(BUILD_TESTING)
  enable_testing()
  add_executable(test_collision_core test/test_collision_core.cpp)
  target_link_libraries(test_collision_core collision_core)
  add_test(NAME collision_core COMMAND test_collision_core)
  add_executable(test_pause_ramp test/test_pause_ramp.cpp)
  target_include_directories(test_pause_ramp PRIVATE include)
  target_compile_options(test_pause_ramp PRIVATE -UNDEBUG)
  add_test(NAME pause_ramp COMMAND test_pause_ramp)
  add_test(NAME protection_mock_api COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/test/mock_protection_integration.py --node $<TARGET_FILE:protection_node>)
  set_tests_properties(protection_mock_api PROPERTIES TIMEOUT 30
    ENVIRONMENT "ROS_DOMAIN_ID=67;ROS_LOCALHOST_ONLY=1")
  add_test(NAME pausable_controller_mock COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/test/mock_pause_integration.py)
  add_test(NAME pausable_controller_native_scaling_mock COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/test/mock_pause_integration.py --native-factor 0.5)
  add_test(NAME four_manager_execution_mock COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/test/mock_cell_execution.py --node $<TARGET_FILE:protection_node>)
  set_tests_properties(protection_mock_api pausable_controller_mock
    pausable_controller_native_scaling_mock four_manager_execution_mock PROPERTIES
    RUN_SERIAL TRUE TIMEOUT 120
    ENVIRONMENT "ROS_DOMAIN_ID=67;ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST;ROS_LOCALHOST_ONLY=1;ROS_LOG_DIR=${CMAKE_CURRENT_BINARY_DIR}/test-logs")
endif()
ament_export_include_directories(include)
ament_export_libraries(collision_core)
ament_export_dependencies(nlohmann_json)
ament_package()
