"""Bound executor bookkeeping under the simulation's high-rate clock.

Default incompatible-QoS/type warning handlers add middleware waitables to every
publisher/subscriber. Lyrical scans these on each clock message. Motion nodes
already detect absent/incompatible inputs through independent freshness and
heartbeat checks, so they do not depend on those warning-only callbacks.
Explicitly supplied event callbacks remain supported; transport QoS is unchanged.
"""
from rclpy.node import Node
from rclpy.event_handler import PublisherEventCallbacks,SubscriptionEventCallbacks


class MotionNode(Node):
    def create_publisher(self,*args,**kwargs):
        if kwargs.get('event_callbacks') is None:
            kwargs['event_callbacks']=PublisherEventCallbacks(use_default_callbacks=False)
        return super().create_publisher(*args,**kwargs)

    def create_subscription(self,*args,**kwargs):
        if kwargs.get('event_callbacks') is None:
            kwargs['event_callbacks']=SubscriptionEventCallbacks(use_default_callbacks=False)
        return super().create_subscription(*args,**kwargs)
