"""Interactive PIE vault checks: a fixture positions the player; press V, then Space when requested by the result phase. Test-only cover changes stay in PIE."""
import unreal as u,json,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'Saved'/'PrototypeTests'/'vault-result.json'
out.parent.mkdir(parents=True,exist_ok=True)
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem);levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
cls=u.load_class(None,'/Game/OFFAIR/Core/BP_RunDirector.BP_RunDirector_C')
s={'phase':'start','status':'running','passed':[],'started':time.monotonic(),'max_height':0}

def phase(p):s['phase']=p;s['entered']=time.monotonic()
def fixture(pawn,pc,pos=(180,-330,98.15),yaw=0):
    pawn.set_actor_location(u.Vector(*pos),False,True)
    pawn.character_movement.stop_movement_immediately()
    pc.set_control_rotation(u.Rotator(pitch=0,yaw=yaw,roll=0))
def check(c,m):
    if not c:raise AssertionError(m)
def record(m):s['passed'].append(m)
def block(w,pos,scale):
    a=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.StaticMeshActor) if a.get_actor_label() in ('OF_CoverLeft','OF_CoverRight','OF_TerminalCover'))
    a.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
    a.set_actor_location(u.Vector(*pos),False,True)
    a.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
    a.set_actor_scale3d(u.Vector(*scale))
    return a
def tick(dt):
    try:
        w=ue.get_game_world()
        if not w:return
        d=u.GameplayStatics.get_actor_of_class(w,cls);pawn=u.GameplayStatics.get_player_pawn(w,0);pc=u.GameplayStatics.get_player_controller(w,0)
        if not d or not d.get_editor_property('Initialized') or d.get_editor_property('Resetting'):return
        now=time.monotonic();p=s['phase'];active=d.get_editor_property('VaultActive');stage=d.get_editor_property('Stage')
        if p=='start':fixture(pawn,pc);phase('setup')
        elif p=='setup' and now-s['entered']>0.5:
            check(d.call_method('CanVault',()),'Expected valid near obstacle')
            fixture(pawn,pc,yaw=180)
            d.call_method('TryVault',());check(not d.get_editor_property('VaultActive'),'Wrong facing accepted');record('wrong_facing_rejected')
            fixture(pawn,pc,pos=(-100,-330,98.15))
            d.call_method('TryVault',());check(not d.get_editor_property('VaultActive'),'Distant vault accepted');record('distance_rejected')
            fixture(pawn,pc);phase('ready_wait')
        elif p=='ready_wait' and now-s['entered']>0.3:
            check('[V]' in d.get_editor_property('PromptText'),'Missing V prompt')
            u.SystemLibrary.execute_console_command(w,'HighResShot 1280x720 filename="'+(out.parent/'vault-prompt.png').as_posix()+'"')
            phase('key_ready')
        elif p=='key_ready' and active:
            record('physical_V_started_vault');phase('moving')
        elif p=='moving':
            s['max_height']=max(s['max_height'],pawn.get_actor_location().z)
            if active:
                before=d.get_editor_property('VaultElapsed');d.call_method('TryVault',())
                check(d.get_editor_property('VaultElapsed')==before,'Duplicate event restarted movement')
            else:
                check(pawn.get_actor_location().x>430,'Did not reach far side')
                check(s['max_height']>200,'Did not climb over obstacle')
                record('swept_vault_crossed_obstacle_and_duplicate_rejected');phase('landed')
        elif p=='landed' and now-s['entered']>0.5:
            check(pawn.character_movement.is_moving_on_ground(),'Did not restore ground movement')
            record('walking_restored');s['jump_base']=pawn.get_actor_location().z;phase('jump_ready')
        elif p=='jump_ready' and pawn.get_actor_location().z>s['jump_base']+15:
            record('physical_SPACE_still_jumps');phase('jump_wait')
        elif p=='jump_wait' and pawn.character_movement.is_moving_on_ground():
            fixture(pawn,pc);phase('landing_block_setup')
        elif p=='landing_block_setup' and now-s['entered']>0.3:
            a=block(w,(460,-330,70),(0.6,1.8,1.4))
            d.call_method('TryVault',());check(not d.get_editor_property('VaultActive'),'Blocked landing accepted')
            a.destroy_actor();record('blocked_landing_rejected')
            a=block(w,(180,-330,310),(1.0,2.0,0.2))
            d.call_method('TryVault',());check(not d.get_editor_property('VaultActive'),'Blocked headroom accepted')
            a.destroy_actor();record('blocked_headroom_rejected')
            obstacle=d.get_editor_property('VaultObstacle');s['obstacle_scale']=obstacle.get_actor_scale3d()
            obstacle.set_actor_scale3d(u.Vector(0.6,2.2,2.5))
            d.call_method('TryVault',());check(not d.get_editor_property('VaultActive'),'Tall wall accepted')
            obstacle.set_actor_scale3d(s['obstacle_scale']);s.pop('obstacle_scale');record('too_tall_rejected')
            d.call_method('TryVault',());check(d.get_editor_property('VaultActive'),'Reset fixture cannot start vault')
            d.call_method('Restart',());phase('death_wait')
        elif p=='death_wait' and stage==0 and not active and now-s['entered']>0.5:
            check(pawn.get_actor_location().x<100,'Death did not restore spawn')
            check(pawn.character_movement.is_moving_on_ground(),'Death retained flight')
            record('death_mid_vault_restores_spawn_and_input')
            fixture(pawn,pc);phase('gm_setup')
        elif p=='gm_setup' and now-s['entered']>0.3:
            d.call_method('TryVault',());check(d.get_editor_property('VaultActive'),'GM fixture cannot start vault')
            d.call_method('GMStage',(1,));phase('gm_wait')
        elif p=='gm_wait' and stage==1 and not active:
            record('gm_reset_clears_vault');d.call_method('GMStage',(1,));phase('remote_wait')
        elif p=='remote_wait' and stage==2:
            d.call_method('EnterRemote',(True,));check(d.get_editor_property('RemoteActive'),'Remote fixture failed')
            d.call_method('TryVault',());check(not d.get_editor_property('VaultActive'),'Remote vault accepted')
            d.call_method('ExitRemote',());record('remote_mode_rejects_vault');phase('finish')
        elif p=='finish':
            s['status']='passed';phase('done')
            u.unregister_slate_post_tick_callback(handle);levels.editor_request_end_play()
        s.update(stage=stage,active=bool(active),seconds=round(now-s['started'],2))
        out.write_text(json.dumps(s,indent=2),encoding='utf-8')
        if now-s['started']>240:raise RuntimeError('timeout')
    except Exception:
        s['status']='failed';s['error']=traceback.format_exc()
        out.write_text(json.dumps(s,indent=2,default=str),encoding='utf-8')
        u.unregister_slate_post_tick_callback(handle);levels.editor_request_end_play()
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
levels.editor_request_begin_play()






