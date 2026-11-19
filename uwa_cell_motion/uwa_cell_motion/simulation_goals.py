"""Convert a preplanned trajectory into a Gazebo controller goal."""
from control_msgs.action import FollowJointTrajectory
from control_msgs.msg import JointTolerance
from trajectory_msgs.msg import JointTrajectoryPoint


def trajectory_goal(trajectory, stamp=None):
    goal = FollowJointTrajectory.Goal()
    names = list(trajectory['joint_names'])
    goal.trajectory.joint_names = names
    if stamp is not None:
        goal.trajectory.header.stamp = stamp
    # FollowJointTrajectory uses -1 to erase controller-default tolerances.
    goal.path_tolerance = [
        JointTolerance(name=name, position=-1., velocity=-1., acceleration=-1.)
        for name in names
    ]
    goal.goal_tolerance = list(goal.path_tolerance)
    for entry in trajectory['points']:
        point = JointTrajectoryPoint(positions=list(entry['positions']))
        if 'velocities' in entry:
            point.velocities = list(entry['velocities'])
        if 'accelerations' in entry:
            point.accelerations = list(entry['accelerations'])
        nanoseconds = round(entry['time'] * 1e9)
        point.time_from_start.sec, point.time_from_start.nanosec = divmod(nanoseconds, 10**9)
        goal.trajectory.points.append(point)
    return goal
