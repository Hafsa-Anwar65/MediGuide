#!/usr/bin/env python3
"""
station_markers
---------------
Shows the pharmacy and the wards on the map in RViz.
Topic: /stations (visualization_msgs/MarkerArray)
"""
import rospy
from visualization_msgs.msg import Marker, MarkerArray


def make_markers(stations):
    arr = MarkerArray()
    for i, (key, s) in enumerate(sorted(stations.items())):
        is_pharmacy = key == "pharmacy"

        dot = Marker()
        dot.header.frame_id = "map"
        dot.ns = "stations"
        dot.id = i * 2
        dot.type = Marker.CYLINDER
        dot.action = Marker.ADD
        dot.pose.position.x = float(s["x"])
        dot.pose.position.y = float(s["y"])
        dot.pose.position.z = 0.02
        dot.pose.orientation.w = 1.0
        dot.scale.x = dot.scale.y = 0.4
        dot.scale.z = 0.04
        dot.color.a = 0.8
        if is_pharmacy:
            dot.color.g = 0.7
        else:
            dot.color.b = 0.9
        arr.markers.append(dot)

        label = Marker()
        label.header.frame_id = "map"
        label.ns = "labels"
        label.id = i * 2 + 1
        label.type = Marker.TEXT_VIEW_FACING
        label.action = Marker.ADD
        label.pose.position.x = float(s["x"])
        label.pose.position.y = float(s["y"])
        label.pose.position.z = 0.5
        label.pose.orientation.w = 1.0
        label.scale.z = 0.35
        label.color.r = label.color.g = label.color.b = 0.1
        label.color.a = 1.0
        label.text = s.get("name", key)
        arr.markers.append(label)
    return arr


if __name__ == "__main__":
    rospy.init_node("stationmarkers")
    pub = rospy.Publisher("/stations", MarkerArray, queue_size=1, latch=True)
    stations = rospy.get_param("/stations", {})
    rate = rospy.Rate(0.5)
    while not rospy.is_shutdown():
        pub.publish(make_markers(stations))
        rate.sleep()
