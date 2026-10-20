"""PIE integration driver: normal interactions, real movement and weapon fire.

Run in UnrealEditor with -ExecutePythonScript=<file> (not a commandlet).
The driver never uses GM actions during the normal-playthrough phase.
"""
import json
import time
import traceback
import sys
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import importlib
import runtime_regressions
run_case = importlib.reload(runtime_regressions).run_case
OUT = ROOT / 'Saved' / 'PrototypeTests'
OUT.mkdir(parents=True, exist_ok=True)
RESULT = OUT / 'runtime-result.json'
LEVEL = '/Game/OFFAIR/Levels/Lvl_Prototype'
DIRECTOR = u.load_class(None, '/Game/OFFAIR/Core/BP_RunDirector.BP_RunDirector_C')
EDITOR = u.get_editor_subsystem(u.LevelEditorSubsystem)
UE = u.get_editor_subsystem(u.UnrealEditorSubsystem)
u.EditorPythonScripting.set_keep_python_script_alive(True)

state = {'phase': 'boot', 'started': time.monotonic(), 'entered': time.monotonic(),
         'passed': [], 'events': [], 'status': 'running', 'last_shot': 0.0,
         'waypoint': 0, 'normal_gm_calls': 0, 'snapshots': []}
handle = None


def record(name, detail=''):
    state['passed'].append(name)
    state['events'].append({'test': name, 'detail': detail, 'seconds': round(time.monotonic() - state['started'], 2)})
    u.log('OFFAIR_TEST_PASS ' + name + ' ' + detail)
    write_result()


def write_result():
    RESULT.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def phase(name):
    state['phase'] = name
    state['entered'] = time.monotonic()
    write_result()


def finish(status, error=''):
    state['status'] = status
    state['error'] = error
    state['elapsed_seconds'] = round(time.monotonic() - state['started'], 2)
    write_result()
    u.log('OFFAIR_TEST_RESULT ' + status + ' ' + error)
    if handle is not None:
        u.unregister_slate_post_tick_callback(handle)
    EDITOR.editor_request_end_play()
    u.EditorPythonScripting.set_keep_python_script_alive(False)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def prop(obj, name):
    return obj.get_editor_property(name)


def invoke(obj, name, *args):
    return obj.call_method(name, args)


def aim(world, pc, target):
    camera = u.GameplayStatics.get_player_camera_manager(world, 0)
    eye = camera.get_camera_location()
    pc.set_control_rotation(u.MathLibrary.find_look_at_rotation(eye, target))


def move_to(pawn, target, tolerance=70.0):
    pos = pawn.get_actor_location()
    dx, dy = target[0] - pos.x, target[1] - pos.y
    distance = (dx * dx + dy * dy) ** 0.5
    if distance <= tolerance:
        pawn.character_movement.stop_movement_immediately()
        return True
    pawn.add_movement_input(u.Vector(dx / distance, dy / distance, 0), 1.0, False)
    return False


def tick(delta):
    try:
        now = time.monotonic()
        require(now - state['started'] < 360, 'Integration run exceeded 360 seconds')
        require(now - state['entered'] < 75, 'Phase timeout: ' + state['phase'])
        world = UE.get_game_world()
        if not world:
            return
        director = u.GameplayStatics.get_actor_of_class(world, DIRECTOR)
        pc = u.GameplayStatics.get_player_controller(world, 0)
        pawn = u.GameplayStatics.get_player_pawn(world, 0)
        if not director or not pc or not pawn:
            return
        if prop(director, 'Resetting'):
            return
        failure = str(prop(director, 'FailureText'))
        require(not failure, 'Run initialization failed: ' + failure)
        if not prop(director, 'Initialized'):
            return
        session = prop(director, 'Session')
        current = int(prop(director, 'Stage'))
        if now - state.get('last_observation', 0) > 2:
            pos = pawn.get_actor_location()
            state['observation'] = {'stage': current, 'position': [pos.x, pos.y, pos.z],
                'hp': float(prop(pawn, 'Current HP')), 'remote': bool(prop(director, 'RemoteActive')),
                'alarm': bool(prop(director, 'Alarm')), 'live_enemies': int(prop(director, 'EnemyCount'))}
            state['last_observation'] = now
            write_result()
        mode = state['phase']
        if mode.startswith('reg_'):
            if run_case(state, world, director, pawn, session, now, require, invoke, record, phase):
                finish('passed')
            return
        if mode == 'boot':
            require(current == 0, 'New game did not begin in stage 0')
            require(pawn.get_class().get_name() == 'BP_OFFAIRPlayer_C', 'Wrong pawn class')
            record('startup', 'OFFAIR player/controller/session/director initialized')
            invoke(director, 'Interact')
            require(not prop(director, 'CoreCollected'), 'Remote-distance pickup was accepted')
            record('interaction_distance_guard')
            state['run_before'] = int(prop(session, 'RunNumber'))
            invoke(director, 'Restart')
            invoke(director, 'Restart')
            require(int(prop(director, 'AcceptedResets')) == 1, 'Death accepted more than once')
            phase('same_stage')
        elif mode == 'same_stage':
            if int(prop(session, 'RunNumber')) <= state['run_before']:
                return
            require(current == 0, 'Death before condition advanced stage')
            record('same_stage_death_and_duplicate_guard')
            phase('anchor')
        elif mode == 'anchor':
            target = prop(director, 'CoreItem').get_actor_location()
            aim(world, pc, target)
            if move_to(pawn, (target.x - 100, target.y)):
                invoke(director, 'Interact')
                require(prop(director, 'CoreCollected'), 'Normal anchor interaction failed')
                require(int(prop(session, 'PendingStage')) == 1, 'Anchor did not latch stage 1')
                require(int(prop(director, 'Stage')) == 0, 'Anchor advanced immediately')
                record('normal_anchor_pickup')
                phase('pending')
        elif mode == 'pending':
            require(current == 0, 'Pending stage applied while alive')
            if now - state['entered'] > 0.7:
                state['run_before'] = int(prop(session, 'RunNumber'))
                invoke(director, 'Restart')
                record('pending_waits_for_death')
                phase('stage1')
        elif mode == 'stage1':
            if current != 1:
                return
            require(int(prop(session, 'PendingStage')) == -1, 'Pending stage not cleared')
            require(prop(director, 'KeyEnemy') is not None, 'Stage 1 guard missing')
            require(not prop(director, 'AccessCollected'), 'Access leaked across reset')
            enemy_pos = prop(director, 'KeyEnemy').get_actor_location()
            nav = u.GameplayStatics.get_all_actors_of_class(world, u.RecastNavMesh)
            require(len(nav) == 1, 'Prototype has no Recast navigation data')
            if 'guard_start' not in state:
                state['guard_start'] = [enemy_pos.x, enemy_pos.y, enemy_pos.z]
            moved = ((enemy_pos.x - state['guard_start'][0])**2 + (enemy_pos.y - state['guard_start'][1])**2)**0.5
            require(moved < 2, 'Guard moved before weapon pickup')
            require(float(prop(pawn, 'Current HP')) == 500.0, 'Guard damaged player before weapon pickup')
            require(prop(pawn, 'Current Weapon') is None, 'Weapon acquired without E interaction')
            if now - state['entered'] < 1.5:
                return
            record('guard_waits_for_weapon')
            invoke(director, 'Interact')
            require(not prop(director, 'WeaponCollected'), 'Distant interaction acquired weapon')
            record('death_applies_next_baseline')
            phase('weapon')
        elif mode == 'weapon':
            pickup = prop(director, 'WeaponPickup')
            if move_to(pawn, (pickup.get_actor_location().x - 140, 0), 20):
                if 'weapon_wait' not in state:
                    state['weapon_wait'] = now
                require(prop(pawn, 'Current Weapon') is None, 'Proximity picked up weapon automatically')
                if now - state['weapon_wait'] < 0.5:
                    return
                aim(world, pc, pickup.get_actor_location() + u.Vector(-1000, 0, 300))
                phase('weapon_look_away')
        elif mode == 'weapon_look_away':
            if now - state['entered'] < 0.15:
                return
            invoke(director, 'Interact')
            require(not prop(director, 'WeaponCollected'), 'Weapon collected while looking away')
            aim(world, pc, invoke(director, 'InteractionPoint', prop(director, 'WeaponPickup')))
            phase('weapon_interact')
        elif mode == 'weapon_interact':
            if now - state['entered'] < 0.15:
                return
            require('[E] Pick up pistol' in prop(director, 'PromptText'), 'Missing E weapon prompt')
            invoke(director, 'Interact')
            if prop(pawn, 'Current Weapon') is not None:
                pawn.character_movement.stop_movement_immediately()
                record('real_weapon_pickup', prop(pawn, 'Current Weapon').get_class().get_name())
                invoke(director, 'Interact')
                require(len(prop(pawn, 'Owned Weapons')) == 1, 'Repeated E duplicated weapon')
                phase('guard_active')
        elif mode == 'guard_active':
            enemy_pos = prop(director, 'KeyEnemy').get_actor_location()
            moved = ((enemy_pos.x - state['guard_start'][0])**2 + (enemy_pos.y - state['guard_start'][1])**2)**0.5
            if moved < 12:
                require(now - state['entered'] < 12, 'Guard did not start after E weapon pickup')
                return
            record('guard_moves_on_navigation', f'{moved:.1f} cm after weapon pickup')
            phase('combat')
        elif mode == 'combat':
            enemy = prop(director, 'KeyEnemy')
            if prop(director, 'GuardRewarded'):
                invoke(pawn, 'Touch Shoot End')
                record('real_weapon_defeats_guard')
                phase('access')
                return
            require(enemy is not None, 'Guard vanished before normal kill reward')
            target = enemy.get_actor_location() + u.Vector(0, 0, 35)
            aim(world, pc, target)
            pawn.character_movement.stop_movement_immediately()
            if now - state['last_shot'] > 0.34:
                invoke(pawn, 'Touch Shoot End')
                invoke(pawn, 'Touch Shoot Start')
                state['last_shot'] = now
            require(current == 1, 'Combat unexpectedly reset stage')
        elif mode == 'access':
            target = prop(director, 'AccessItem').get_actor_location()
            aim(world, pc, target)
            if move_to(pawn, (target.x - 110, target.y), 55):
                invoke(director, 'Interact')
                require(prop(director, 'AccessCollected'), 'Normal access-card pickup failed')
                record('normal_access_card_pickup')
                state['waypoint'] = 0
                phase('camera_approach')
        elif mode == 'camera_approach':
            route = [(1800, 0)]
            waypoint = route[state['waypoint']]
            target = prop(director, 'Monitor').get_actor_location()
            aim(world, pc, target)
            if move_to(pawn, waypoint, 40):
                state['waypoint'] += 1
                if state['waypoint'] == len(route):
                    phase('camera_interact')
        elif mode == 'camera_interact':
            if now - state['entered'] < 0.15:
                return
            require(prop(director, 'CameraPromptVisible'), 'Camera hack prompt missing')
            body_pos = pawn.get_actor_location()
            state['body_before_remote'] = [body_pos.x, body_pos.y, body_pos.z]
            invoke(director, 'Interact')
            require(prop(director, 'RemoteActive'), 'Looking at camera did not hack it')
            record('normal_monitor_hack')
            phase('remote')
        elif mode == 'remote':
            invoke(director, 'PanRemote', 1000.0, 1000.0)
            require(abs(float(prop(director, 'RemoteYaw')) - 280) < 0.01, 'Yaw limit failed')
            require(abs(float(prop(director, 'RemotePitch')) - 5) < 0.01, 'Pitch upper limit failed')
            invoke(director, 'PanRemote', 0.0, -1000.0)
            require(abs(float(prop(director, 'RemotePitch')) + 45) < 0.01, 'Pitch lower limit failed')
            before = state['body_before_remote']
            pos = pawn.get_actor_location()
            require(abs(pos.x - before[0]) < 5 and abs(pos.y - before[1]) < 5, 'Body moved during remote control')
            invoke(director, 'ExitRemote')
            require(not prop(director, 'RemoteActive'), 'Camera did not exit')
            record('remote_rotation_clamps_and_body_restore')
            state['waypoint'] = 0
            phase('escape')
        elif mode == 'escape':
            route = [(2090, -410), (2090, 0), (2360, 0), (3030, 0), (3570, 0)]
            if prop(director, 'Completed'):
                require(not prop(director, 'Alarm'), 'Completed despite alarm')
                record('normal_playthrough_complete', 'No GM action was used; real movement, pickup, weapon projectiles and direct camera interaction')
                phase('done')
                return
            require(not prop(director, 'Alarm'), 'Rotated camera still detected escape route')
            waypoint = route[min(state['waypoint'], len(route) - 1)]
            aim(world, pc, u.Vector(waypoint[0] + 150, waypoint[1], 150))
            if move_to(pawn, waypoint, 15):
                state['waypoint'] = min(state['waypoint'] + 1, len(route) - 1)
        elif mode == 'done':
            require(state['normal_gm_calls'] == 0, 'Normal run used GM')
            invoke(director, 'Restart')
            phase('reg_start')
    except Exception:
        finish('failed', traceback.format_exc())


# Preserve unsaved map edits when validating in the already-open editor.
editor_world = UE.get_editor_world()
if not editor_world or editor_world.get_path_name().split('.')[0] != LEVEL:
    require(EDITOR.load_level(LEVEL), 'Prototype map could not load')
handle = u.register_slate_post_tick_callback(tick)
EDITOR.editor_request_begin_play()
write_result()
