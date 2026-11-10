from glob import glob
from setuptools import find_packages,setup

setup(name='uwa_cell_visualization',version='0.1.0',packages=find_packages(),
    data_files=[('share/ament_index/resource_index/packages',['resource/uwa_cell_visualization']),
                ('share/uwa_cell_visualization',['package.xml']),
                ('share/uwa_cell_visualization/launch',glob('launch/*.launch.py'))],
    install_requires=['setuptools'],zip_safe=True,maintainer='rosmatch',
    maintainer_email='rosmatch@example.com',license='MIT',
    description='Read-only measured UR visualization',
    entry_points={'console_scripts':['hardware_overlay = uwa_cell_visualization.bridge:main']})
