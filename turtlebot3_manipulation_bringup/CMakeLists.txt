################################################################################
# Set minimum required version of cmake, project name and compile options
################################################################################
cmake_minimum_required(VERSION 3.5)
project(turtlebot3_manipulation_bringup)

################################################################################
# Find and load build settings from external packages
################################################################################
find_package(ament_cmake REQUIRED)

################################################################################
# Install
################################################################################
install(
  DIRECTORY launch config rviz
  DESTINATION share/${PROJECT_NAME}
)

################################################################################
# Macro for ament package
################################################################################
install(PROGRAMS ../tools/teleop ../tools/gpu_inputs ../tools/gpu_h264 DESTINATION lib/${PROJECT_NAME})
ament_package()
