from setuptools import setup,find_packages
from glob import glob

setup(name='uwa_cell_tracking',version='0.1.0',packages=find_packages(),
    data_files=[('share/ament_index/resource_index/packages',['resource/uwa_cell_tracking']),
                ('share/uwa_cell_tracking',['package.xml']),
                ('share/uwa_cell_tracking/launch',glob('launch/*.launch.py'))],
    install_requires=['setuptools'],zip_safe=True,maintainer='rosmatch',maintainer_email='rosmatch@example.com',
    license='MIT',description='Camera-relative CPU object localization and tracking',
    entry_points={'console_scripts':['object_pose = uwa_cell_tracking.cli:main','object_tracker = uwa_cell_tracking.node:main',
                                    'oak_tracking_stream = uwa_cell_tracking.oak_stream:main']})
