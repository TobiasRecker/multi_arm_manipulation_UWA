"""Gazebo adapters for the shared description configuration."""
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET
import yaml

from uwa_cell_description.configuration import (
    ROBOT_IDS, JOINT_SUFFIXES, TOOLS_KEYS, SCAN_DEFAULTS, default_layout_path,
    nominal_layout_path, number, vector, load_layout, joint_names, gripper_joint,
    controller_names, controller_parameters,
)


def without_image_sensors(description):
    """Keep all physical/visual bodies and joints; omit image rendering only."""
    root=ET.fromstring(description)
    for parent in root.iter():
        for child in list(parent):
            kind=child.get('type','')
            if child.tag=='sensor' and ('camera' in kind or kind in ('depth','rgbd')):parent.remove(child)
    return ET.tostring(root,encoding='unicode')


def render_description(layout, directory, *, image_sensors=True):
    """Generate only temporary launch artifacts, never edit the source layout."""
    import xacro
    from ament_index_python.packages import get_package_share_directory
    directory = Path(directory)
    layout = deepcopy(layout)
    if layout['charuco']['enabled']:
        from .charuco import prepare_assets
        prepare_assets(layout['charuco'], directory / 'charuco')
    layout_file, controllers_file = directory / 'layout.yaml', directory / 'controllers.yaml'
    layout_file.write_text(yaml.safe_dump(layout))
    controllers_file.write_text(yaml.safe_dump(controller_parameters(layout)))
    xacro_file = Path(get_package_share_directory('uwa_cell_description')) / 'urdf/cell.urdf.xacro'
    description = xacro.process_file(str(xacro_file), mappings={
        'layout': str(layout_file), 'controllers_file': str(controllers_file),
    }).toxml()
    from uwa_cell_description.calibration_profile import apply_description
    description = apply_description(description, layout)
    if not image_sensors:description=without_image_sensors(description)
    return description, controllers_file
