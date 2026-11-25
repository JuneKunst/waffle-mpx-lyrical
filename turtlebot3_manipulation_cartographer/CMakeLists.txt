################################################################################
# Set minimum required version of cmake, project name and compile options
################################################################################
cmake_minimum_required(VERSION 3.5)
project(turtlebot3_manipulation_cartographer)

################################################################################
# Find ament packages and libraries for ament and system dependencies
################################################################################
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(Eigen3 REQUIRED)
find_package(visualization_msgs REQUIRED)
find_package(cartographer_ros_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(urdf REQUIRED)
find_path(CARTOGRAPHER_ROS_INCLUDE cartographer_ros/node.h REQUIRED)
find_path(ABSL_INCLUDE absl/synchronization/mutex.h REQUIRED)
find_path(LUA_INCLUDE lua.hpp PATH_SUFFIXES lua5.2 lua5.3 lua5.4 REQUIRED)
find_library(CARTOGRAPHER_ROS_LIBRARY cartographer_ros REQUIRED)
find_package(cartographer REQUIRED)
find_library(GLOG_LIBRARY glog REQUIRED)
add_executable(online_node src/online_node.cpp)
target_compile_features(online_node PRIVATE cxx_std_17)
target_include_directories(online_node PRIVATE ${CARTOGRAPHER_ROS_INCLUDE} ${ABSL_INCLUDE} ${LUA_INCLUDE})
target_link_libraries(online_node PRIVATE ${CARTOGRAPHER_ROS_LIBRARY} cartographer ${GLOG_LIBRARY}
  Eigen3::Eigen rclcpp::rclcpp tf2_ros::tf2_ros urdf::urdf
  ${cartographer_ros_msgs_TARGETS} ${visualization_msgs_TARGETS} ${nav_msgs_TARGETS} ${sensor_msgs_TARGETS})
install(TARGETS online_node DESTINATION lib/${PROJECT_NAME})
# Include Cartographer's own Lua modules when its runtime is installed in a local prefix.
find_path(CARTOGRAPHER_LUA_DIR map_builder.lua PATH_SUFFIXES share/cartographer/configuration_files REQUIRED)
install(DIRECTORY ${CARTOGRAPHER_LUA_DIR}/ DESTINATION share/${PROJECT_NAME}/config)

################################################################################
# Install
################################################################################
install(
  DIRECTORY config launch rviz
  DESTINATION share/${PROJECT_NAME}
)

################################################################################
# Macro for ament package
################################################################################
ament_package()
