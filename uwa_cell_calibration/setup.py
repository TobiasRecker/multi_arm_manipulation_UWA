from glob import glob
from setuptools import setup, find_packages
setup(name='uwa_cell_calibration', version='0.1.0', packages=find_packages(),
 data_files=[('share/ament_index/resource_index/packages',['resource/uwa_cell_calibration']),
 ('share/uwa_cell_calibration',['package.xml']),('share/uwa_cell_calibration/launch',glob('launch/*.launch.py'))],
 install_requires=['setuptools'], zip_safe=True, maintainer='rosmatch', maintainer_email='rosmatch@example.com',
 description='Supervised UWA eye-in-hand calibration', license='MIT',
 entry_points={'console_scripts':[
 'calibration_backend = uwa_cell_calibration.backend:main',
 'calibration_gui = uwa_cell_calibration.gui:main',
 'calibration_cli = uwa_cell_calibration.cli:main',
 'calibration_solve = uwa_cell_calibration.solver:main']})
