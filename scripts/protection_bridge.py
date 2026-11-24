#!/usr/bin/env python3
"""Persistent JSON-lines transport for the minimal UWA protection API.

This client never invokes the legacy guard or Dashboard STOP. Closing the
transport does not issue any robot command.
"""
import argparse
import json
import os
import queue
import sys
import threading
import time


ARMS = ('left_front', 'left_rear', 'right_front', 'right_rear')
OPERATIONS = ('pause_all', 'resume_all', 'status')
PREFIX = '/uwa_cell/protection/'


def emit(packet):
    print(json.dumps(packet, allow_nan=False, separators=(',', ':')), flush=True)


def response_packet(operation, request_id, response):
    packet = dict(event='command_result', operation=operation, id=request_id,
                  phase='done' if response.success else 'failed',
                  success=bool(response.success), message=response.message)
    try:
        value = json.loads(response.message)
        if isinstance(value, dict):
            packet['status'] = value
            if not response.success:
                packet['message'] = str(value.get('command_error') or value.get('error')
                                        or value.get('reason') or 'Command rejected.')
    except (ValueError, TypeError):
        pass
    return packet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('mock', 'hardware'), required=True)
    args = parser.parse_args(argv)
    # The mode is explicit even when launched from a shell with another domain.
    os.environ['ROS_DOMAIN_ID'] = '67' if args.mode == 'mock' else '66'
    os.environ['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
    os.environ['RCUTILS_LOGGING_USE_STDOUT'] = '0'
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from std_msgs.msg import String
    from std_srvs.srv import Trigger

    incoming = queue.Queue()

    def read_requests():
        for line in sys.stdin:
            try:
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise ValueError('A JSON object is required')
                incoming.put(request)
            except (ValueError, TypeError) as error:
                incoming.put(dict(invalid=str(error)))
        incoming.put(None)

    class Bridge(Node):
        def __init__(self):
            super().__init__('uwa_power_protection_bridge')
            self.api_clients = {op: self.create_client(Trigger, PREFIX + op) for op in OPERATIONS}
            self.pending = {}
            self.next_poll = 0.
            self.finished = False
            qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             reliability=ReliabilityPolicy.RELIABLE)
            self.create_subscription(String, PREFIX + 'status', self.receive_status, qos)
            self.create_timer(.02, self.tick)
            emit(dict(event='transport', mode=args.mode, phase='running'))

        def receive_status(self, message):
            try:
                status = json.loads(message.data)
                if not isinstance(status, dict):
                    raise ValueError('Expected status object')
                emit(dict(event='status', available=True, status=status))
            except (ValueError, TypeError) as error:
                emit(dict(event='status', available=False, error='Invalid status: ' + str(error)))

        def request(self, operation, request_id):
            client = self.api_clients[operation]
            if not client.service_is_ready():
                packet = dict(event='command_result', operation=operation, id=request_id,
                              phase='failed', success=False,
                              message='Minimal protection endpoint unavailable; command not sent.')
                if operation == 'status':
                    packet = dict(event='status', available=False, error=packet['message'])
                emit(packet)
                return
            if operation != 'status':
                emit(dict(event='command_result', operation=operation, id=request_id, phase='running'))
            try:
                future = client.call_async(Trigger.Request())
                self.pending[request_id] = (operation, future, time.monotonic())
            except Exception as error:
                emit(dict(event='status', available=False, error=str(error)) if operation == 'status' else
                     dict(event='command_result', operation=operation, id=request_id,
                          phase='failed', success=False, message=str(error)))

        def tick(self):
            now = time.monotonic()
            for request_id, (operation, future, sent) in list(self.pending.items()):
                if future.done():
                    del self.pending[request_id]
                    try:
                        packet = response_packet(operation, request_id, future.result())
                        if operation == 'status':
                            packet = dict(event='status', available=packet['success'] and 'status' in packet,
                                          status=packet.get('status'), error='' if packet['success'] else packet['message'])
                        emit(packet)
                    except Exception as error:
                        emit(dict(event='status', available=False, error=str(error)) if operation == 'status' else
                             dict(event='command_result', operation=operation, id=request_id,
                                  phase='failed', success=False, message='Command outcome unconfirmed: ' + str(error)))
                elif now - sent > 2.:
                    self.api_clients[operation].remove_pending_request(future)
                    del self.pending[request_id]
                    emit(dict(event='status', available=False, error='Protection status response unavailable.') if operation == 'status' else
                         dict(event='command_result', operation=operation, id=request_id,
                              phase='failed', success=False, message='No response; command outcome unconfirmed.'))
            # Only status is retried. Operator commands are never replayed after reconnect.
            if now >= self.next_poll and not any(p[0] == 'status' for p in self.pending.values()):
                self.next_poll = now + 1.
                self.request('status', 'status')
            for _ in range(32):
                try:
                    request = incoming.get_nowait()
                except queue.Empty:
                    break
                if request is None:
                    self.finished = True
                    return
                operation = request.get('op')
                request_id = request.get('id')
                if (operation not in OPERATIONS or not isinstance(request_id, str)
                        or not request_id or len(request_id) > 128 or request_id == 'status'):
                    emit(dict(event='protocol_error', phase='failed', message='Invalid operation or request id.'))
                    continue
                if request_id in self.pending:
                    emit(dict(event='protocol_error', phase='failed', message='Request id is already pending.'))
                    continue
                emit(dict(event='command_result', operation=operation, id=request_id, phase='received'))
                self.request(operation, request_id)

    rclpy.init(args=[])
    node = Bridge()
    threading.Thread(target=read_requests, daemon=True).start()
    try:
        while rclpy.ok() and not node.finished:
            rclpy.spin_once(node, timeout_sec=.1)
    except (KeyboardInterrupt, BrokenPipeError):
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
