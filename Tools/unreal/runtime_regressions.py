"""Isolated GM/reset/surveillance cases after the no-GM playthrough.

Position changes here are explicit fixtures for detection-boundary testing,
not substitutes for the normal-playthrough movement/interaction assertions.
"""
import unreal as u


def run_case(state, world, director, pawn, session, now, require, invoke, record, phase):
    mode = state['phase']
    current = int(director.get_editor_property('Stage'))
    run = int(session.get_editor_property('RunNumber'))

    def p(name):
        return director.get_editor_property(name)

    def gm(index):
        state['regression_gm_calls'] = state.get('regression_gm_calls', 0) + 1
        invoke(director, 'GMAction', index)

    def baseline():
        require(not p('WeaponCollected'), 'Weapon pickup state leaked across reset')
        require(not p('RemoteActive') and not p('GMOpen'), 'Input/control mode leaked across reset')
        require(not p('AccessCollected') and not p('HackedOnce') and not p('Alarm'), 'Run progress leaked across reset')
        require(abs(float(p('RemoteYaw')) - 180) < 0.01, 'Camera direction was not reset')
        require(int(p('EnemyCount')) == (1 if current == 1 else 0), 'Wrong baseline enemy count')
        require(len(p('Enemies')) == int(p('EnemyCount')), 'Enemy registry contains stale entries')
        require(len(u.GameplayStatics.get_all_actors_of_class(world, u.PlayerController)) == 1, 'Duplicate player controllers')
        require(len(u.GameplayStatics.get_all_actors_of_class(world, u.AIController)) == int(p('EnemyCount')), 'Orphan AI controllers')

    if mode == 'reg_start':
        require(current == 0, 'New game did not restore stage 0')
        baseline()
        record('completed_restart_restores_new_game')
        invoke(director, 'GMStage', -1)
        invoke(director, 'RequestReset', 99)
        require(not p('Resetting') and current == int(p('Stage')), 'Invalid target changed stage')
        record('stage_boundary_and_invalid_target_guards')
        invoke(session, 'SetGMEnabled', False)
        for action in range(6):
            gm(action)
        invoke(director, 'ToggleGM')
        require(not p('Resetting') and not p('GMOpen') and not p('RemoteActive') and int(p('EnemyCount')) == 0,
                'A GM entry remained active when disabled')
        invoke(session, 'SetGMEnabled', True)
        record('gm_disable_guards_all_entries')
        state['wait_run'] = run
        gm(1)
        phase('reg_stage1')
    elif mode == 'reg_stage1':
        if run <= state['wait_run']:
            return False
        require(current == 1, 'GM next stage failed')
        baseline()
        gm(1)
        require(not p('Resetting'), 'Last stage advanced past its boundary')
        invoke(director, 'EnterRemote', False)
        require(not p('RemoteActive'), 'Normal hack bypassed missing access card')
        gm(5)
        require(p('RemoteActive'), 'GM hack failed to bypass access gate')
        record('normal_permission_and_gm_override')
        state['wait_run'] = run
        gm(0)
        require(not p('RemoteActive'), 'Death did not release remote view immediately')
        phase('reg_remote_death')
    elif mode == 'reg_remote_death':
        if run <= state['wait_run']:
            return False
        baseline()
        record('remote_death_restores_input_and_camera')
        guard = p('KeyEnemy')
        for _ in range(2):
            gm(3)
        require(int(p('EnemyCount')) == 3, 'Two GM spawns did not create two AI instances')
        gm(4)
        gm(4)
        require(int(p('EnemyCount')) == 1 and p('KeyEnemy') == guard, 'GM removal did not prioritize extras')
        gm(4)
        require(int(p('EnemyCount')) == 0 and not p('GuardRewarded'), 'GM removal awarded a real kill')
        gm(4)
        require(int(p('EnemyCount')) == 0, 'Removal below zero changed count')
        record('gm_enemy_lifecycle_and_no_kill_reward')
        state['wait_run'] = run
        gm(0)
        phase('reg_device_loss')
    elif mode == 'reg_device_loss':
        if run <= state['wait_run']:
            return False
        baseline()
        gm(5)
        p('Monitor').destroy_actor()
        phase('reg_device_loss_wait')
    elif mode == 'reg_device_loss_wait':
        if now - state['entered'] < 0.2:
            return False
        require(not p('RemoteActive'), 'Destroyed monitor stranded the player in remote control')
        record('monitor_loss_returns_to_body')
        state['repeat_count'] = 0
        state['wait_run'] = run
        gm(0)
        phase('reg_repeat')
    elif mode == 'reg_repeat':
        if run <= state['wait_run']:
            return False
        baseline()
        state['repeat_count'] += 1
        if state['repeat_count'] >= 10:
            record('ten_reset_cycles_without_state_or_actor_leaks')
            if current == 0:
                state['wait_run'] = run
                gm(1)
            phase('reg_alarm')
            return False
        gm(5)
        invoke(director, 'PanRemote', 800.0, 0.0)
        state['wait_run'] = run
        if state['repeat_count'] % 2:
            gm(2 if current == 1 else 1)
        else:
            gm(0)
    elif mode == 'reg_alarm':
        if current != 1:
            return False
        baseline()
        pawn.set_actor_location(u.Vector(2450, 0, 100), False, True)
        phase('reg_alarm_wait')
    elif mode == 'reg_alarm_wait':
        if now - state['entered'] < 0.7:
            return False
        require(p('Alarm'), 'Default camera failed to detect the player body')
        require(p('ExitGate').get_actor_enable_collision(), 'Alarm did not lock the route')
        record('default_camera_detection_and_alarm_lock')
        state['wait_run'] = run
        gm(0)
        phase('reg_blindspot')
    elif mode == 'reg_blindspot':
        if run <= state['wait_run']:
            return False
        baseline()
        gm(5)
        invoke(director, 'PanRemote', 1000.0, 0.0)
        invoke(director, 'ExitRemote')
        pawn.set_actor_location(u.Vector(2450, 0, 100), False, True)
        phase('reg_blindspot_wait')
    elif mode == 'reg_blindspot_wait':
        if now - state['entered'] < 0.7:
            return False
        require(not p('Alarm'), 'Turned camera still detected the same corridor position')
        require(not p('Completed') and not p('AccessCollected'), 'GM hack fabricated normal completion prerequisites')
        record('camera_orientation_changes_real_detection')
        state['wait_run'] = run
        gm(2)
        phase('reg_kill_condition_setup')
    elif mode == 'reg_kill_condition_setup':
        if run <= state['wait_run']:
            return False
        require(current == 0, 'Kill-condition fixture did not return to stage 0')
        director.set_editor_property('ConditionEvent', 'EnemyKilled')
        director.set_editor_property('ConditionTarget', 'Guard')
        invoke(director, 'InitializeRun')
        require(p('Initialized') and p('KeyEnemy') is not None, 'Alternative condition configuration failed')
        invoke(director, 'MarkCondition', 'ItemAcquired', 'Anchor')
        require(int(session.get_editor_property('PendingStage')) == -1, 'Wrong event satisfied kill condition')
        gm(3)
        extra = list(p('Enemies'))[-1]
        require(extra != p('KeyEnemy'), 'No non-key enemy for condition test')
        u.GameplayStatics.apply_damage(extra, 10000, u.GameplayStatics.get_player_controller(world, 0), pawn, None)
        phase('reg_wrong_kill')
    elif mode == 'reg_wrong_kill':
        if now - state['entered'] < 0.3:
            return False
        require(int(session.get_editor_property('PendingStage')) == -1, 'Non-key enemy advanced the stage')
        u.GameplayStatics.apply_damage(p('KeyEnemy'), 10000, u.GameplayStatics.get_player_controller(world, 0), pawn, None)
        phase('reg_key_kill')
    elif mode == 'reg_key_kill':
        if now - state['entered'] < 0.3:
            return False
        require(int(session.get_editor_property('PendingStage')) == 1 and int(p('Stage')) == 0,
                'Designated kill did not latch the next stage while retaining current stage')
        invoke(director, 'MarkCondition', 'EnemyKilled', 'Guard')
        require(int(p('Stage')) == 0, 'Duplicate key event advanced immediately')
        record('configured_kill_condition_and_wrong_target_rejection')
        state['wait_run'] = int(session.get_editor_property('RunNumber'))
        invoke(director, 'Restart')
        phase('reg_bad_config')
    elif mode == 'reg_bad_config':
        if run <= state['wait_run']:
            return False
        require(current == 1, 'Death after kill condition failed to advance')
        director.set_editor_property('ConditionTarget', 'MissingTarget')
        invoke(director, 'InitializeRun')
        require(not p('Initialized') and bool(p('FailureText')), 'Invalid stage definition entered a playable state')
        require(int(session.get_editor_property('CurrentStage')) == 1, 'Initialization error rolled back progress')
        state['wait_run'] = int(session.get_editor_property('RunNumber'))
        invoke(director, 'RequestReset', 1)
        phase('reg_recovery')
    elif mode == 'reg_recovery':
        if run <= state['wait_run']:
            return False
        baseline()
        require(current == 1 and not p('FailureText'), 'Recovery failed to restore valid stage configuration')
        record('initialization_failure_recovers_without_losing_progress')
        return True
    return False
