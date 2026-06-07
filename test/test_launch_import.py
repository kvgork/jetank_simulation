"""Import-level tests for the jetank_simulation launch files.

These tests load each launch module by path (the files live under ``launch/``
with dotted names like ``gazebo.launch.py`` and are not importable as ordinary
package modules) and call ``generate_launch_description()`` for real. Each call
exercises the package's own code: package-share resolution and (for the files
that build a robot description) xacro processing. We assert that a real
``LaunchDescription`` comes back with the expected number of top-level actions,
which locks in behaviour against accidental additions/removals.

The launch deps (``launch``, ``launch_ros``, ``ament_index_python``, ``xacro``)
are part of the ROS2 / RoboStack env this package builds in, so no stubbing is
needed; if ``ament_index_python`` cannot resolve the installed package shares
(e.g. running outside the colcon overlay) the affected test is skipped rather
than failing spuriously.
"""

import importlib.util
import os

import pytest

from launch import LaunchDescription

LAUNCH_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'launch')

# (filename, expected number of top-level actions in the LaunchDescription)
LAUNCH_FILES = [
    ('gazebo.launch.py', 16),
    ('gazebo_headless.launch.py', 11),
    ('gazebo_remote.launch.py', 3),
    ('robot_remote.launch.py', 6),
]


def _load_launch_module(filename):
    """Load a launch file by path as a standalone module."""
    path = os.path.join(LAUNCH_DIR, filename)
    spec = importlib.util.spec_from_file_location(
        'jetank_sim_' + filename.replace('.', '_'), path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _generate(module):
    """Call generate_launch_description, skipping if package shares are missing."""
    from ament_index_python.packages import PackageNotFoundError
    try:
        return module.generate_launch_description()
    except PackageNotFoundError as exc:
        pytest.skip(f'required package share not installed: {exc}')


@pytest.mark.parametrize('filename, _expected', LAUNCH_FILES)
def test_launch_file_has_generate_function(filename, _expected):
    """Every launch file exposes a callable generate_launch_description()."""
    module = _load_launch_module(filename)
    assert callable(module.generate_launch_description)


@pytest.mark.parametrize('filename, expected_actions', LAUNCH_FILES)
def test_generate_launch_description_returns_launch_description(filename, expected_actions):
    """generate_launch_description() returns a LaunchDescription with the expected actions."""
    module = _load_launch_module(filename)
    ld = _generate(module)
    assert isinstance(ld, LaunchDescription)
    assert len(ld.entities) == expected_actions


def test_gazebo_declares_expected_launch_arguments():
    """The full gazebo launch declares use_sim_time, world, and start_arm_active."""
    from launch.actions import DeclareLaunchArgument

    module = _load_launch_module('gazebo.launch.py')
    ld = _generate(module)
    declared = {
        a.name for a in ld.entities if isinstance(a, DeclareLaunchArgument)
    }
    assert {'use_sim_time', 'world', 'start_arm_active'} <= declared
