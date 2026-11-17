from setuptools import find_packages, setup
from glob import glob

setup(name='uwa_cell_gripper_control',version='0.1.0',packages=find_packages(),
      data_files=[('share/ament_index/resource_index/packages',['resource/uwa_cell_gripper_control']),
                  ('share/uwa_cell_gripper_control',['package.xml']),
                  ('share/uwa_cell_gripper_control/launch',glob('launch/*.launch.py'))],
      install_requires=['setuptools'],zip_safe=True,maintainer='rosmatch',
      maintainer_email='rosmatch@example.com',license='MIT',
      description='Shared four-arm Robotiq action/service control',
      entry_points={'console_scripts':['cell_gripper_node = uwa_cell_gripper_control.node:main',
                                      'cell_gripper = uwa_cell_gripper_control.client:main']})
