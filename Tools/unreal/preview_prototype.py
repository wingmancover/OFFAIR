"""Temporary rendered PIE session for screenshot and real-key/button checks.

It walks to the first item and aims at it, but never performs the interaction.
All UI input is left to the operator. No assets or gameplay defaults are saved.
"""
import json
import time
from pathlib import Path
import unreal as u

out = Path(__file__).resolve().parents[2] / 'Saved' / 'PrototypeTests'
out.mkdir(parents=True, exist_ok=True)
command = out / 'preview-command.txt'
if command.exists():
    command.unlink()
levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
director_cls = u.load_class(None, '/Game/OFFAIR/Core/BP_RunDirector.BP_RunDirector_C')
u.EditorPythonScripting.set_keep_python_script_alive(True)
start = time.monotonic()
prepared = False
interacted = False
last_write = 0.0
callback = None


def end():
    if callback is not None:
        u.unregister_slate_post_tick_callback(callback)
    levels.editor_request_end_play()
    u.EditorPythonScripting.set_keep_python_script_alive(False)
    u.SystemLibrary.quit_editor()


def tick(dt):
    global prepared, interacted, last_write
    try:
        if time.monotonic() - start > 600:
            end()
            return
        if command.exists() and command.read_text(encoding='utf-8').strip() == 'finish':
            command.unlink()
            end()
            return
        world = editor.get_game_world()
        if not world:
            return
        director = u.GameplayStatics.get_actor_of_class(world, director_cls)
        player = u.GameplayStatics.get_player_pawn(world, 0)
        controller = u.GameplayStatics.get_player_controller(world, 0)
        if not director or not player or not controller or not director.get_editor_property('Initialized'):
            return
        if director.get_editor_property('CoreCollected'):
            interacted = True
        if not interacted and int(director.get_editor_property('Stage')) == 0 and not director.get_editor_property('RemoteActive'):
            core = director.get_editor_property('CoreItem').get_actor_location()
            camera = u.GameplayStatics.get_player_camera_manager(world, 0)
            controller.set_control_rotation(u.MathLibrary.find_look_at_rotation(camera.get_camera_location(), core))
            pos = player.get_actor_location()
            dx, dy = core.x - 110 - pos.x, core.y - pos.y
            dist = (dx * dx + dy * dy)**0.5
            if dist > 20 and not director.get_editor_property('GMOpen'):
                player.add_movement_input(u.Vector(dx/dist, dy/dist, 0), 1, False)
            else:
                player.character_movement.stop_movement_immediately()
                prepared = True
        if command.exists():
            action = command.read_text(encoding='utf-8').strip()
            command.unlink()
            if action == 'finish':
                end()
                return
            if action == 'capture':
                u.SystemLibrary.execute_console_command(world, 'HighResShot 1280x720')
        if time.monotonic() - last_write > 0.5:
            pos = player.get_actor_location()
            result = {name: director.get_editor_property(name) for name in [
                'Initialized', 'Stage', 'CoreCollected', 'AccessCollected', 'RemoteActive',
                'GMOpen', 'Alarm', 'Completed', 'EnemyCount', 'PromptText', 'StatusText',
                'RemoteYaw', 'RemotePitch']}
            result['ready_for_input'] = prepared
            result['position'] = [pos.x, pos.y, pos.z]
            (out / 'preview-state.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            last_write = time.monotonic()
    except PermissionError:
        # Windows can briefly lock the command/state file while an external
        # operator writes or reads it. Retry on the next editor frame.
        return
    except Exception as e:
        (out / 'preview-error.txt').write_text(str(e), encoding='utf-8')
        end()


assert levels.load_level('/Game/OFFAIR/Levels/Lvl_Prototype')
callback = u.register_slate_post_tick_callback(tick)
levels.editor_request_begin_play()
