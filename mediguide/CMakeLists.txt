cmake_minimum_required(VERSION 3.0.2)
project(mediguide)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  message_generation
)

add_service_files(
  FILES
  GetRoute.srv
)

generate_messages(
  DEPENDENCIES
  std_msgs
)

catkin_package(
  CATKIN_DEPENDS rospy std_msgs message_runtime
)

catkin_install_python(PROGRAMS
  scripts/deliverymanager.py
  scripts/routeserver.py
  scripts/stationmarkers.py
  scripts/nursepanel.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch config maps worlds
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
