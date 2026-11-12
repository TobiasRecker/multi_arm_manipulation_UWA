from setuptools import setup,find_packages
from glob import glob

setup(name='uwa_cell_control',version='0.1.0',packages=find_packages(),
      data_files=[('share/ament_index/resource_index/packages',['resource/uwa_cell_control']),
                  ('share/uwa_cell_control',['package.xml']),
                  ('share/uwa_cell_control/launch',glob('launch/*.launch.py')),
                  ('share/uwa_cell_control/remote',glob('remote/*.py')+glob('remote/*.c'))],
      install_requires=['setuptools'],zip_safe=True,maintainer='rosmatch',
      maintainer_email='rosmatch@example.com',license='MIT',
      description='UWA local multi-arm preparation GUI',
      entry_points={'console_scripts':['uwa_control_gui = uwa_cell_control.gui:main',
                                      'park_arm = uwa_cell_control.park_arm:main',
                                      'handeye_hardware = uwa_cell_control.handeye_hardware:main',
                                      'wrist_camera_gui = uwa_cell_control.wrist_camera_gui:main',
                                      'board_capture_gui = uwa_cell_control.board_capture_gui:main',
                                      'digitize_box = uwa_cell_control.object_digitization:main',
                                      'object_scan_plan = uwa_cell_control.object_scan_plan:main',
                                      'wrist_hd_service = uwa_cell_control.wrist_hd_service:main']})
