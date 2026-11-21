#!/usr/bin/env python3
"""
route_server
------------
Gives the route between the ward and the pharmacy.

Service: /getroute  (mediguide/GetRoute)
  - steps : directions for the real robot, e.g. "F150,R90,F400,L90,F100,U"
  - x, y, yaw : position of the destination on the Gazebo map

The route to the pharmacy is written in config/stations.yaml.
The way back is the same path in reverse: the order of steps is flipped and
every right turn becomes a left turn (and the other way round).
At the end of each trip the robot turns around (U), so it is ready for the next trip.
"""
import rospy
from mediguide.srv import GetRoute, GetRouteResponse


def reverse_route(steps):
    back = []
    for s in reversed(steps):
        if s[0] == "R":
            back.append("L" + s[1:])
        elif s[0] == "L":
            back.append("R" + s[1:])
        else:
            back.append(s)
    return back


class RouteServer:
    def __init__(self):
        self.stations = rospy.get_param("/stations", {})
        to_pharmacy = [str(s).strip().upper() for s in rospy.get_param("/route_to_pharmacy", [])]
        self.routes = {
            ("ward", "pharmacy"): to_pharmacy + ["U"],
            ("pharmacy", "ward"): reverse_route(to_pharmacy) + ["U"],
        }
        rospy.loginfo("Route to pharmacy: %s", ",".join(self.routes[("ward", "pharmacy")]))
        rospy.loginfo("Route to ward:     %s", ",".join(self.routes[("pharmacy", "ward")]))
        rospy.Service("getroute", GetRoute, self.handle)

    def handle(self, req):
        res = GetRouteResponse()
        goal = self.stations.get(req.to_station)
        steps = self.routes.get((req.from_station, req.to_station))
        if goal is None or steps is None:
            rospy.logwarn("No route: %s -> %s", req.from_station, req.to_station)
            res.ok = False
            return res

        res.ok = True
        res.steps = ",".join(steps)
        res.x = float(goal["x"])
        res.y = float(goal["y"])
        res.yaw = float(goal["yaw"])
        return res


if __name__ == "__main__":
    rospy.init_node("routeserver")
    RouteServer()
    rospy.spin()
