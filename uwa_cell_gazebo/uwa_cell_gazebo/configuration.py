"""Gazebo adapters for the shared description configuration."""
from copy import deepcopy
from pathlib import Path
import yaml

from uwa_cell_description.configuration import (
    ROBOT_IDS, JOINT_SUFFIXES, TOOLS_KEYS, SCAN_DEFAULTS, default_layout_path,
    nominal_layout_path, number, vector, load_layout, joint_names, gripper_joint,
    controller_names, controller_parameters,
)


def render_description(layout, directory):
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
    return description, controllers_file
