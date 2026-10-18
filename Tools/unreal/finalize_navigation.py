"""Build navigation after real editor frames have registered map geometry.

A NavData Actor alone is insufficient: we require successful projections on
both gameplay bays and the corridor. Run through Tools/Run-Unreal.ps1 Build.
"""
import json
import time
from pathlib import Path
import unreal as u

out = Path(__file__).resolve().parents[2] / 'Saved' / 'PrototypeBuild'
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
u.EditorPythonScripting.set_keep_python_script_alive(True)
assert levels.load_level('/Game/OFFAIR/Levels/Lvl_Prototype')
started = time.monotonic()
busy = False
handle = None


def finalize(dt):
    global busy
    if busy or time.monotonic() - started < 3.0:
        return
    # Build utilities pump Slate. Unregister before invoking them so this
    # one-shot callback cannot recursively build navigation.
    busy = True
    u.unregister_slate_post_tick_callback(handle)
    result_path = out / 'build-result.json'
    result = json.loads(result_path.read_text(encoding='utf-8'))
    result['navigation_ready'] = False
    try:
        world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        u.SystemLibrary.execute_console_command(world, 'BUILDPATHS')
        data = u.GameplayStatics.get_all_actors_of_class(world, u.RecastNavMesh)
        if len(data) != 1:
            raise RuntimeError(f'Expected one Recast actor, found {len(data)}')
        nav = data[0]
        nav.set_actor_label('OF_RecastNavMesh')
        for field, expected in [('agent_radius', 48.0), ('agent_height', 192.0)]:
            if abs(nav.get_editor_property(field) - expected) > 0.01:
                raise RuntimeError(f'Navigation {field} does not match the template character')
        points = []
        for x in [0, 800, 1550, 2400]:
            projected = u.NavigationSystemV1.project_point_to_navigation(
                world, u.Vector(x, 0, 50), nav, None, u.Vector(200, 200, 400))
            if projected is None:
                raise RuntimeError(f'No walkable navigation surface near x={x}')
            points.append([projected.x, projected.y, projected.z])
        assert levels.save_current_level()
        result['navigation_ready'] = True
        result['navigation_actor'] = nav.get_path_name()
        result['navigation_projections'] = points
        level_path = out / 'level-result.json'
        level = json.loads(level_path.read_text(encoding='utf-8'))
        level['nav_data_count'] = 1
        level['actor_count'] = len(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
        level_path.write_text(json.dumps(level, indent=2), encoding='utf-8')
        u.log('OFFAIR_NAVIGATION_READY projections verified')
    except Exception as error:
        result['navigation_error'] = str(error)
        u.log_error('OFFAIR_NAVIGATION_FAILED ' + str(error))
    finally:
        result_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
        u.EditorPythonScripting.set_keep_python_script_alive(False)


handle = u.register_slate_post_tick_callback(finalize)
