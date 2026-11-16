#!/usr/bin/env python3
"""Source-tree entry point for the independently tested ROS gripper adapter."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'uwa_cell_tasks'))
from uwa_cell_tasks.hardware_gripper_node import main
if __name__=='__main__':main()
