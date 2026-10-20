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
        require(not p('TrapTriggered') and not p('SystemResetActive'), 'Narrative trigger state leaked across reset')
        require(int(p('EnemyCount')) == (1 if current == 2 else 0), 'Wrong baseline enemy count')
        require(float(pawn.get_editor_property('Current HP')) == (100 if current == 1 else 500), 'Stage health leaked across reset')
        require(len(p('Enemies')) == int(p('EnemyCount')), 'Enemy registry contains stale entries')
        require(len(u.GameplayStatics.get_all_actors_of_class(world, u.PlayerController)) == 1, 'Duplicate player controllers')
        require(len(u.GameplayStatics.get_all_actors_of_class(world, u.AIController)) == int(p('EnemyCount')), 'Orphan AI controllers')

    def look_at(target):
        pc = u.GameplayStatics.get_player_controller(world, 0)
        camera = u.GameplayStatics.get_player_camera_manager(world, 0)
        pc.set_control_rotation(u.MathLibrary.find_look_at_rotation(camera.get_camera_location(), target))

    def place_and_look(position, target):
        pawn.set_actor_location(u.Vector(*position), False, True)
        pawn.character_movement.stop_movement_immediately()
        # Use the current body's eye height, avoiding the previous camera cache.
        pc = u.GameplayStatics.get_player_controller(world, 0)
        eye = pawn.get_actor_location() + u.Vector(0, 0, 71)
        pc.set_control_rotation(u.MathLibrary.find_look_at_rotation(eye, target))

    if mode == 'reg_start':
        require(current == 0, 'New game did not restore stage 0')
        baseline()
        record('completed_restart_restores_new_game')
        place_and_look((3600, 0, 100), u.Vector(3800, 0, 100))
        invoke(director, 'CheckFinish')
        require(not p('Completed'), 'Stage 0 could finish before narrative progression')
        place_and_look((-160, 0, 98), u.Vector(245, -170, 1.5))
        record('stage0_cannot_complete_early')
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
        record('gm_trap_stage_baseline')
        state['wait_run'] = run
        invoke(director, 'Restart')
        phase('reg_trap_retry')
    elif mode == 'reg_trap_retry':
        if run <= state['wait_run']:
            return False
        baseline()
        require(current == 1, 'Death before box interaction advanced the trap stage')
        record('trap_death_before_box_retries_same_stage')
        phase('reg_trap_thought_expiry')
    elif mode == 'reg_trap_thought_expiry':
        if float(p('ThoughtRemaining')) > 0:
            require(now-state['entered'] < 6, 'First thought did not expire')
            return False
        require(p('ThoughtText') == '', 'Expired thought text was retained')
        record('first_thought_expires_after_three_seconds')
        place_and_look((670, 0, 98), p('TrapBox').get_actor_location())
        phase('reg_trap_interrupt')
    elif mode == 'reg_trap_interrupt':
        if now-state['entered'] < 0.6:
            return False
        invoke(director, 'Interact')
        require(p('TrapTriggered') and int(session.get_editor_property('PendingStage')) == 2, 'Trap fixture failed')
        state['wait_run'] = run
        gm(2)
        phase('reg_note_interrupt_setup')
    elif mode == 'reg_note_interrupt_setup':
        if run <= state['wait_run']:
            return False
        baseline()
        require(current == 0 and int(session.get_editor_property('PendingStage')) == -1, 'GM jump retained trap pending progress')
        record('gm_interrupt_clears_trap_enemy_and_pending_stage')
        place_and_look((125, -170, 98), p('CoreItem').get_actor_location())
        phase('reg_note_interrupt')
    elif mode == 'reg_note_interrupt':
        if now-state['entered'] < 0.6:
            return False
        invoke(director, 'Interact')
        require(p('SystemResetActive'), 'Note interruption fixture failed')
        state['wait_run'] = run
        # Internal failure/isolation fixture, not a user-facing bypass of the lock.
        invoke(director, 'RequestReset', 2)
        phase('reg_old_countdown')
    elif mode == 'reg_old_countdown':
        if run <= state['wait_run']:
            return False
        baseline()
        require(current == 2, 'Countdown isolation fixture reached wrong stage')
        state['isolated_run'] = run
        phase('reg_old_countdown_wait')
    elif mode == 'reg_old_countdown_wait':
        require(run == state['isolated_run'], 'Old note countdown killed a new attempt')
        if now-state['entered'] < 3.5:
            return False
        require(p('ThoughtText') == '' and float(p('ThoughtRemaining')) == 0, 'Second thought did not expire')
        record('old_countdown_isolated_and_second_thought_expires')
        phase('reg_stage2')
    elif mode == 'reg_stage2':
        if run <= state['wait_run']:
            return False
        require(current == 2, 'GM next stage did not reach combat stage')
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
            if current != 2:
                state['wait_run'] = run
                gm(1)
            phase('reg_alarm')
            return False
        gm(5)
        invoke(director, 'PanRemote', 800.0, 0.0)
        state['wait_run'] = run
        if state['repeat_count'] % 2:
            gm(2 if current == 2 else 1)
        else:
            gm(0)
    elif mode == 'reg_alarm':
        if current != 2:
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
        if current == 1:
            state['wait_run'] = run
            gm(2)
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
        state['wait_run'] = run
        gm(1)
        phase('reg_combat_recovered')
    elif mode == 'reg_combat_recovered':
        if run <= state['wait_run']:
            return False
        require(current == 2, 'Recovery fixture did not reach combat stage')
        baseline()
        place_and_look((655, 0, 98), invoke(director, 'InteractionPoint', p('WeaponPickup')))
        phase('reg_weapon_model')
    elif mode == 'reg_weapon_model':
        if now - state['entered'] < 0.6:
            return False
        point = invoke(director, 'InteractionPoint', p('WeaponPickup'))
        center = u.SystemLibrary.get_component_bounds(p('WeaponPickup').get_editor_property('StaticMesh'))[0]
        require((point-center).length() < 1.0, 'Weapon aim point does not follow rendered mesh bounds')
        require(invoke(director, 'CanInteract', p('WeaponPickup')), 'Looking at visible gun model cannot interact')
        look_at(p('WeaponPickup').get_actor_location())
        phase('reg_weapon_base')
    elif mode == 'reg_weapon_base':
        if now - state['entered'] < 0.6:
            return False
        require(not invoke(director, 'CanInteract', p('WeaponPickup')), 'Looking at gun plinth still triggers pickup')
        record('weapon_targets_visible_model_instead_of_plinth')
        place_and_look((1800, 0, 98), p('Monitor').get_actor_location())
        phase('reg_direct_no_access')
    elif mode == 'reg_direct_no_access':
        if now - state['entered'] < 0.6:
            return False
        require(invoke(director, 'CanInteract', p('Monitor')), 'Camera fixture is not visible')
        require(not p('CameraPromptVisible'), 'Hack prompt offered before acquiring card')
        invoke(director, 'Interact')
        require(not p('RemoteActive'), 'Direct camera hack bypassed permission')
        record('direct_camera_requires_access_card')
        # Explicit boundary fixture: kill through normal damage and collect the real drop.
        u.GameplayStatics.apply_damage(p('KeyEnemy'), 10000, u.GameplayStatics.get_player_controller(world, 0), pawn, None)
        invoke(director, 'PollEnemies')
        card = p('AccessItem').get_actor_location()
        place_and_look((card.x - 110, card.y, 98), card)
        phase('reg_direct_collect_card')
    elif mode == 'reg_direct_collect_card':
        if now - state['entered'] < 0.6:
            return False
        invoke(director, 'Interact')
        require(p('AccessCollected'), 'Boundary fixture could not collect real access card')
        place_and_look((1800, 0, 98), p('Monitor').get_actor_location())
        phase('reg_direct_clear')
    elif mode == 'reg_direct_clear':
        if now - state['entered'] < 0.6:
            return False
        require(p('CameraPromptVisible'), f"Visible authorized camera has no prompt: access={p('AccessCollected')} remote={p('RemoteActive')} can={invoke(director, 'CanInteract', p('Monitor'))}")
        invoke(director, 'Interact')
        require(p('RemoteActive') and not p('CameraPromptVisible'), 'Direct hack did not enter or clear prompt')
        before = float(p('RemotePitch'))
        invoke(director, 'PanRemote', 0.0, 20.0)
        require(float(p('RemotePitch')) > before, 'Positive mouse Y did not pitch upward')
        invoke(director, 'PanRemote', 0.0, -40.0)
        require(float(p('RemotePitch')) < before, 'Negative mouse Y did not pitch downward')
        invoke(director, 'ExitRemote')
        record('direct_camera_enters_and_pitch_sign_is_consistent')
        pc = u.GameplayStatics.get_player_controller(world, 0)
        pc.set_control_rotation(u.Rotator(0, 90, 0))
        phase('reg_direct_look_away')
    elif mode == 'reg_direct_look_away':
        if now - state['entered'] < 0.6:
            return False
        require(not p('CameraPromptVisible'), 'Camera prompt remains when looking away')
        invoke(director, 'EnterRemote', False)
        require(not p('RemoteActive'), 'Normal entry bypassed camera aim check')
        record('direct_camera_rejects_looking_away')
        place_and_look((1100, 0, 98), p('Monitor').get_actor_location())
        phase('reg_direct_distance')
    elif mode == 'reg_direct_distance':
        if now - state['entered'] < 0.6:
            return False
        invoke(director, 'EnterRemote', False)
        require(not p('RemoteActive') and not p('CameraPromptVisible'), 'Camera accepted out-of-range hack')
        record('direct_camera_rejects_beyond_1500_cm')
        place_and_look((1830, -410, 98), p('Monitor').get_actor_location())
        phase('reg_direct_wall')
    elif mode == 'reg_direct_wall':
        if now - state['entered'] < 0.6:
            return False
        require(pawn.get_distance_to(p('Monitor')) < 1500, 'Wall fixture is also out of range')
        require(not invoke(director, 'CanInteract', p('Monitor')), 'Camera interaction passed through corridor side wall')
        invoke(director, 'EnterRemote', False)
        require(not p('RemoteActive') and not p('CameraPromptVisible'), 'Wall did not block prompt/entry')
        record('direct_camera_wall_blocks_prompt_and_entry')
        place_and_look((1800, 0, 98), p('Monitor').get_actor_location())
        phase('reg_direct_restored')
    elif mode == 'reg_direct_restored':
        if now - state['entered'] < 0.6:
            return False
        require(p('CameraPromptVisible'), 'Camera prompt did not return after clearing obstruction')
        legacy = [a for a in u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
                  if a.get_actor_label() in ('OF_Terminal', 'OF_TerminalScreen', 'OF_TerminalLabel')]
        require(len(legacy) == 3 and all(a.get_editor_property('hidden') and not a.get_actor_enable_collision() for a in legacy),
                'Legacy terminal remains visible or blocking after reset')
        record('direct_camera_prompt_recovers_and_legacy_terminal_hidden')
        return True
    return False
