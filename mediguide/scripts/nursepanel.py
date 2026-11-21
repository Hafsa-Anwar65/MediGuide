#!/usr/bin/env python3
"""
nurse_panel
-----------
Keyboard version of the two push buttons, for the Gazebo simulation.
Run it in its own terminal:

    rosrun mediguide nursepanel.py

  w  -> nurse presses the Ward button (send robot to the pharmacy)
  r  -> pharmacist presses Return (send robot back to the ward)
  q  -> quit
"""
import rospy
from std_msgs.msg import String

KEYS = {"w": "ward", "r": "return"}


def on_status(msg):
    print("\n  ROBOT: %s" % msg.data)


if __name__ == "__main__":
    rospy.init_node("nursepanel", disable_signals=True)
    pub = rospy.Publisher("/robot/button", String, queue_size=1)
    rospy.Subscriber("/robot/status", String, on_status)
    rospy.sleep(0.5)

    print("=" * 50)
    print(" MediGuide buttons")
    print("  w : Ward button (nurse)")
    print("  r : Return button (pharmacist)")
    print("  q : quit")
    print("=" * 50)

    while not rospy.is_shutdown():
        try:
            key = input("Press a button: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if key == "q":
            break
        if key in KEYS:
            pub.publish(String(data=KEYS[key]))
            print("  -> sent '%s'" % KEYS[key])
        else:
            print("  Use w, r or q")

    rospy.signal_shutdown("quit")
