#!/usr/bin/env python3
"""Camera-only native HD service for the older left-front CB3 controller."""
import sys
from uwa_cell_control import wrist_hd_service
from uwa_cell_control.wrist_hd import LeftFrontNativeCapture

ARM = 'left_front'


def main():
    wrist_hd_service.NativeCapture = LeftFrontNativeCapture
    sys.argv = [sys.argv[0], '--arm', ARM]
    return wrist_hd_service.main()


if __name__ == '__main__':
    raise SystemExit(main())
