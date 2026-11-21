#!/usr/bin/env python3
"""
delivery_manager
----------------
The "brain" of MediGuide. It runs the full delivery cycle:

  1. Robot waits in the ward with the lid open.
  2. Nurse puts the slip in the tray and presses the Ward button.
  3. Lid closes, robot goes to the pharmacy.
  4. At the pharmacy the lid opens. The pharmacist reads the slip, puts the
     medicine in the tray and presses Return.
  5. Lid closes, robot goes back to the ward and opens the lid.

Topics (same names on the real robot and in simulation):
  sub  /robot/button    std_msgs/String  "ward" | "return"
  sub  /robot/arrived   std_msgs/Bool    real robot: ESP32 finished the route
  sub  /robot/obstacle  std_msgs/Bool    real robot: something is in front
  pub  /robot/go        std_msgs/String  real robot: directions, e.g. "F150,R90,F400,U"
  pub  /robot/lid       std_msgs/Bool    True = open, False = closed
  pub  /robot/status    std_msgs/String  what the robot is doing now

Parameter ~mode : "sim" (uses move_base in Gazebo) or "real" (uses the ESP32).
"""
import math
import threading

import rospy
import actionlib
from std_msgs.msg import String, Bool
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from actionlib_msgs.msg import GoalStatus
from mediguide.srv import GetRoute

AT_WARD = "AT_WARD"
GOING_TO_PHARMACY = "GOING_TO_PHARMACY"
AT_PHARMACY = "AT_PHARMACY"
GOING_TO_WARD = "GOING_TO_WARD"


class DeliveryManager:
    def __init__(self):
        self.mode = rospy.get_param("~mode", "sim")
        self.current = rospy.get_param("/start_station", "ward")
        self.state = AT_WARD if self.current == "ward" else AT_PHARMACY
        self.lock = threading.RLock()

        self.go_pub = rospy.Publisher("/robot/go", String, queue_size=1)
        self.lid_pub = rospy.Publisher("/robot/lid", Bool, queue_size=1, latch=True)
        self.status_pub = rospy.Publisher("/robot/status", String, queue_size=1, latch=True)

        rospy.wait_for_service("getroute")
        self.get_route = rospy.ServiceProxy("getroute", GetRoute)

        self.move_base = None
        if self.mode == "sim":
            self.move_base = actionlib.SimpleActionClient("move_base", MoveBaseAction)
            rospy.loginfo("Waiting for move_base ...")
            self.move_base.wait_for_server()

        rospy.Subscriber("/robot/button", String, self.on_button)
        rospy.Subscriber("/robot/arrived", Bool, self.on_arrived)
        rospy.Subscriber("/robot/obstacle", Bool, self.on_obstacle)

        self.set_lid(True)
        self.say("Ready in the ward. Put the slip in the tray and press the Ward button.")

    # ---------- helpers ----------
    def say(self, text):
        rospy.loginfo("[%s] %s", self.state, text)
        self.status_pub.publish(String(data=text))

    def set_lid(self, is_open):
        self.lid_pub.publish(Bool(data=is_open))
        rospy.loginfo("Lid %s", "OPEN" if is_open else "CLOSED")

    def go_to(self, station):
        route = self.get_route(self.current, station)
        if not route.ok:
            self.say("No route from %s to %s" % (self.current, station))
            return

        if self.mode == "real":
            rospy.loginfo("Sending directions: %s", route.steps)
            self.go_pub.publish(String(data=route.steps))
        else:
            goal = MoveBaseGoal()
            goal.target_pose.header.frame_id = "map"
            goal.target_pose.header.stamp = rospy.Time.now()
            goal.target_pose.pose.position.x = route.x
            goal.target_pose.pose.position.y = route.y
            goal.target_pose.pose.orientation.z = math.sin(route.yaw / 2.0)
            goal.target_pose.pose.orientation.w = math.cos(route.yaw / 2.0)
            self.move_base.send_goal(goal, done_cb=self.on_move_base_done)

    # ---------- callbacks ----------
    def on_button(self, msg):
        button = msg.data.strip().lower()
        with self.lock:
            if button == "ward" and self.state == AT_WARD:
                self.set_lid(False)
                self.state = GOING_TO_PHARMACY
                self.say("Order received. Going to the pharmacy.")
                self.go_to("pharmacy")

            elif button == "return" and self.state == AT_PHARMACY:
                self.set_lid(False)
                self.state = GOING_TO_WARD
                self.say("Medicine loaded. Going back to the ward.")
                self.go_to("ward")

            else:
                rospy.logwarn("Button '%s' ignored in state %s", button, self.state)

    def on_arrived(self, msg):
        if not msg.data:
            return
        with self.lock:
            if self.state == GOING_TO_PHARMACY:
                self.current = "pharmacy"
                self.state = AT_PHARMACY
                self.set_lid(True)
                self.say("At the pharmacy. Read the slip, put the medicine in the tray and press Return.")
            elif self.state == GOING_TO_WARD:
                self.current = "ward"
                self.state = AT_WARD
                self.set_lid(True)
                self.say("Medicine delivered. Please take it from the tray.")

    def on_move_base_done(self, status, result):
        if status == GoalStatus.SUCCEEDED:
            self.on_arrived(Bool(data=True))
        else:
            rospy.logwarn("move_base could not reach the goal (status %d). Trying again in 3 s.", status)
            rospy.Timer(rospy.Duration(3.0), self.retry, oneshot=True)

    def retry(self, _event):
        with self.lock:
            if self.state == GOING_TO_PHARMACY:
                self.go_to("pharmacy")
            elif self.state == GOING_TO_WARD:
                self.go_to("ward")

    def on_obstacle(self, msg):
        if msg.data:
            self.say("Something is in front of the robot. Waiting for the way to clear.")
        else:
            self.say("Way is clear. Moving again.")


if __name__ == "__main__":
    rospy.init_node("deliverymanager")
    DeliveryManager()
    rospy.spin()
