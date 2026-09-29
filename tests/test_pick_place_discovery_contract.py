from pathlib import Path

import yaml


ROOT = Path(__file__).resolve()
while ROOT.name != 'PhyAgentOS-forge' and ROOT.parent != ROOT:
    ROOT = ROOT.parent

SUPPORTED_SENSOR_REFS = {
    'camera/head',
    'camera/front',
    'camera/left_wrist',
    'camera/right_wrist',
}


def _find_properties(value):
    if isinstance(value, dict):
        properties = value.get('properties')
        if isinstance(properties, dict):
            yield properties
        for child in value.values():
            yield from _find_properties(child)
    elif isinstance(value, list):
        for child in value:
            yield from _find_properties(child)


def _tool_properties(path, required_key):
    document = yaml.safe_load((ROOT / path).read_text(encoding='utf-8'))
    return next(props for props in _find_properties(document) if required_key in props)


def test_scene_observe_exposes_supported_sensor_inventory():
    properties = _tool_properties('examples/forge-skills/pick-place-workflow/contracts/scene.observe.tool.yaml', 'sensor_refs')
    assert set(properties['sensor_ref']['enum']) == SUPPORTED_SENSOR_REFS
    assert set(properties['sensor_refs']['items']['enum']) == SUPPORTED_SENSOR_REFS
    assert properties['sensor_refs']['minItems'] == 2
    assert properties['sensor_refs']['uniqueItems'] is True
