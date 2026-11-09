#!/usr/bin/env python3
"""Restore the cell's existing XWayland windows without restarting ROS."""
import argparse
import ctypes as C
import os
from pathlib import Path
import subprocess
import time


class MessageData(C.Union):
    _fields_ = [('b', C.c_char * 20), ('s', C.c_short * 10), ('l', C.c_long * 5)]


class ClientMessage(C.Structure):
    _fields_ = [('type', C.c_int), ('serial', C.c_ulong), ('send_event', C.c_int),
                ('display', C.c_void_p), ('window', C.c_ulong),
                ('message_type', C.c_ulong), ('format', C.c_int), ('data', MessageData)]


class Event(C.Union):
    _fields_ = [('client', ClientMessage), ('pad', C.c_long * 24)]


class WindowError(C.Structure):
    _fields_ = [('type', C.c_int), ('display', C.c_void_p), ('resource', C.c_ulong),
                ('serial', C.c_ulong), ('code', C.c_ubyte),
                ('request', C.c_ubyte), ('minor', C.c_ubyte)]


class Desktop:
    def __init__(self):
        self.x = C.CDLL('libX11.so.6')
        signatures = {
            'XOpenDisplay': ([C.c_char_p], C.c_void_p),
            'XDefaultRootWindow': ([C.c_void_p], C.c_ulong),
            'XInternAtom': ([C.c_void_p, C.c_char_p, C.c_int], C.c_ulong),
            'XGetWindowProperty': ([C.c_void_p, C.c_ulong, C.c_ulong, C.c_long,
                C.c_long, C.c_int, C.c_ulong, C.POINTER(C.c_ulong), C.POINTER(C.c_int),
                C.POINTER(C.c_ulong), C.POINTER(C.c_ulong),
                C.POINTER(C.POINTER(C.c_ubyte))], C.c_int),
            'XSendEvent': ([C.c_void_p, C.c_ulong, C.c_int, C.c_long,
                            C.POINTER(Event)], C.c_int),
            'XMapRaised': ([C.c_void_p, C.c_ulong], C.c_int),
            'XFlush': ([C.c_void_p], C.c_int),
            'XFree': ([C.c_void_p], C.c_int),
            'XCloseDisplay': ([C.c_void_p], C.c_int),
            'XSetErrorHandler': ([C.c_void_p], C.c_void_p),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self.x, name)
            function.argtypes, function.restype = arguments, result
        self.display = self.x.XOpenDisplay(os.environ.get('DISPLAY', ':0').encode())
        if not self.display:
            raise RuntimeError('Cannot open the XWayland desktop display')
        callback = C.CFUNCTYPE(C.c_int, C.c_void_p, C.POINTER(WindowError))
        self.error_callback = callback(self.window_error)
        self.previous_handler = self.x.XSetErrorHandler(C.cast(self.error_callback, C.c_void_p))
        self.root = self.x.XDefaultRootWindow(self.display)

    @staticmethod
    def window_error(display, event):
        # A startup splash can disappear between enumeration and activation.
        # BadWindow is an expected race, not a reason to abort the app launcher.
        if event.contents.code != 3:
            print(f'Window activation error: X11 code {event.contents.code}', flush=True)
        return 0

    def atom(self, name):
        return self.x.XInternAtom(self.display, name.encode(), False)

    def property(self, window, name):
        actual, count, remaining = C.c_ulong(), C.c_ulong(), C.c_ulong()
        fmt, data = C.c_int(), C.POINTER(C.c_ubyte)()
        code = self.x.XGetWindowProperty(self.display, window, self.atom(name),
            0, 4096, False, 0, C.byref(actual), C.byref(fmt), C.byref(count),
            C.byref(remaining), C.byref(data))
        if code or not data:
            return []
        try:
            if fmt.value == 32:
                return list(C.cast(data, C.POINTER(C.c_ulong))[:count.value])
            if fmt.value == 8:
                return C.string_at(data, count.value).decode(errors='replace')
            return []
        finally:
            self.x.XFree(data)

    def windows(self, pids):
        result = []
        for window in self.property(self.root, '_NET_CLIENT_LIST'):
            owner = self.property(window, '_NET_WM_PID')
            if owner and owner[0] in pids:
                types = self.property(window, '_NET_WM_WINDOW_TYPE')
                if types and not any(kind in types for kind in (
                        self.atom('_NET_WM_WINDOW_TYPE_NORMAL'),
                        self.atom('_NET_WM_WINDOW_TYPE_DIALOG'))):
                    continue
                result.append((window, self.property(window, 'WM_CLASS')))
        return result

    def activate(self, window):
        self.x.XMapRaised(self.display, window)
        event = Event()
        event.client.type = 33  # ClientMessage
        event.client.display = self.display
        event.client.window = window
        event.client.message_type = self.atom('_NET_ACTIVE_WINDOW')
        event.client.format = 32
        event.client.data.l[0] = 2  # Desktop/pager activation, requested by the user.
        event.client.data.l[1] = 0  # CurrentTime
        self.x.XSendEvent(self.display, self.root, False, (1 << 20) | (1 << 19),
                         C.byref(event))
        self.x.XFlush(self.display)

    def close(self):
        self.x.XCloseDisplay(self.display)
        self.x.XSetErrorHandler(self.previous_handler)


def service_pids():
    result = set()
    for unit in ('uwa-cell-sim', 'uwa-cell-rviz'):
        group = subprocess.check_output(['systemctl', '--user', 'show', unit,
            '--property=ControlGroup', '--value'], text=True).strip()
        if not group.startswith('/') or group == '/':
            continue
        directory = Path('/sys/fs/cgroup') / group.lstrip('/')
        for file in directory.rglob('cgroup.procs'):
            try:
                result.update(int(pid) for pid in file.read_text().split())
            except FileNotFoundError:
                pass  # A child process may finish during startup.
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefer', choices=('gazebo', 'rviz'), default='gazebo')
    args = parser.parse_args()
    desktop = Desktop()
    try:
        deadline = time.monotonic() + 20
        while True:
            windows = desktop.windows(service_pids())
            classes = ' '.join(str(name) for _, name in windows)
            if ('gz-sim-gui' in classes and 'rviz2' in classes) or time.monotonic() >= deadline:
                break
            time.sleep(.25)
        preferred = 'gz-sim-gui' if args.prefer == 'gazebo' else 'rviz2'
        # Last activation receives focus. Restrict all windows to our service PIDs.
        windows.sort(key=lambda item: preferred in str(item[1]))
        for window, name in windows:
            desktop.activate(window)
            time.sleep(.1)
            print(f'Restored cell window {window:#x}: {name!r}', flush=True)
        if not windows:
            print('Cell services started, but no desktop window appeared within 20 seconds.')
    finally:
        desktop.close()


if __name__ == '__main__':
    main()
