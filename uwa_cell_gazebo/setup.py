from glob import glob
from setuptools import find_packages, setup

setup(
    name='uwa_cell_gazebo', version='0.1.0', packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/uwa_cell_gazebo']),
        ('share/uwa_cell_gazebo', ['package.xml']),
        ('share/uwa_cell_gazebo/launch', glob('launch/*.launch.py')),
        ('share/uwa_cell_gazebo/worlds', glob('worlds/*.sdf') + glob('worlds/*.config')),
        ('share/uwa_cell_gazebo/rviz', glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'], extras_require={'test': ['pytest']}, zip_safe=True,
    maintainer='rosmatch', maintainer_email='rosmatch@example.com', license='MIT',
    description='UWA four-arm Gazebo cell',
    entry_points={'console_scripts': [
        'prepare_scan = uwa_cell_gazebo.scan:main',
        'scan_reference = uwa_cell_gazebo.scan_reference:main',
        'verify_cell = uwa_cell_gazebo.verify_cell:main',
        'clock_bridge = uwa_cell_gazebo.clock_bridge:main',
    ]},
)
