#!/bin/bash
# MediGuide setup for Ubuntu 20.04 + ROS Noetic
# Run from inside the MediGuide folder:
#     bash setup.sh
set -e

echo "==== MediGuide setup ===="

# 1. Check Ubuntu version
UBUNTU=$(lsb_release -rs)
if [ "$UBUNTU" != "20.04" ]; then
  echo "WARNING: ROS Noetic needs Ubuntu 20.04. You have $UBUNTU."
  echo "Stop here and send this message to Claude."
  exit 1
fi

# 2. Install ROS Noetic if it is not installed
if [ ! -f /opt/ros/noetic/setup.bash ]; then
  echo "==== Installing ROS Noetic (this takes a while) ===="
  sudo apt update
  sudo apt install -y curl gnupg2 lsb-release
  sudo sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list'
  curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | sudo apt-key add -
  sudo apt update
  sudo apt install -y ros-noetic-desktop-full
fi

# 3. Install the packages this project uses
echo "==== Installing project packages ===="
sudo apt update
sudo apt install -y \
  ros-noetic-turtlebot3 ros-noetic-turtlebot3-msgs ros-noetic-turtlebot3-simulations \
  ros-noetic-navigation ros-noetic-map-server ros-noetic-amcl ros-noetic-move-base \
  ros-noetic-dwa-local-planner ros-noetic-global-planner \
  ros-noetic-gmapping ros-noetic-slam-gmapping \
  ros-noetic-rosserial ros-noetic-rosserial-python ros-noetic-rosserial-arduino \
  ros-noetic-teleop-twist-keyboard ros-noetic-xacro

# 4. Make the catkin workspace and copy the package
source /opt/ros/noetic/setup.bash
mkdir -p ~/catkin_ws/src
rm -rf ~/catkin_ws/src/mediguide
cp -r "$(dirname "$0")/mediguide" ~/catkin_ws/src/
chmod +x ~/catkin_ws/src/mediguide/scripts/*.py ~/catkin_ws/src/mediguide/tools/*.py

# 5. Build
cd ~/catkin_ws
catkin_make

# 6. Add to ~/.bashrc so every new terminal is ready
grep -q "source /opt/ros/noetic/setup.bash" ~/.bashrc || echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc
grep -q "source ~/catkin_ws/devel/setup.bash" ~/.bashrc || echo "source ~/catkin_ws/devel/setup.bash" >> ~/.bashrc
grep -q "TURTLEBOT3_MODEL" ~/.bashrc || echo "export TURTLEBOT3_MODEL=burger" >> ~/.bashrc

echo ""
echo "==== DONE ===="
echo "Close this terminal, open a new one, and run:"
echo "    roslaunch mediguide simulation.launch"
