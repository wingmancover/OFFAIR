"""Actual offscreen PIE frames: HUD, hidden answer and camera-only answer. No desktop input."""
import json
import time
import traceback
from pathlib import Path
import unreal as u

OUT=Path(__file__).resolve().parents[2]/'Saved/RegionLoop'
LEVELS=u.get_editor_subsystem(u.LevelEditorSubsystem)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
shots=['spawn','note','pattern-player','pattern-camera','pattern-player-same-view','gm','saved-b','dome']
index=0; phase='wait'; busy=False; handle=None; entered=time.monotonic(); started=entered
report={'status':'running','captures':[],'method':'RenderOffscreen PIE; same-pose pawn versus CameraActor visibility comparison'}

def finish(error=None):
    report.update(status='failed' if error else 'passed',error=error)
    (OUT/'visual-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    u.unregister_slate_post_tick_callback(handle)
    LEVELS.editor_request_end_play()
    u.EditorPythonScripting.set_keep_python_script_alive(False)
    u.SystemLibrary.quit_editor()

def tick(dt):
    global busy,phase,entered,index
    if busy:return
    busy=True
    try:
        if time.monotonic()-started>200:raise TimeoutError(phase)
        world=UE.get_game_world()
        if not world:return
        p=u.GameplayStatics.get_player_character(world,0); pc=u.GameplayStatics.get_player_controller(world,0)
        ds=u.GameplayStatics.get_all_actors_of_class(world,u.load_class(None,'/Game/OFFAIR/Region/BP_RegionLoopDirector.BP_RegionLoopDirector_C'))
        if not p or not pc or not ds or not ds[0].get_editor_property('Initialized'):return
        d=ds[0]
        actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
        def key(s):d.call_method('HandleRegionInput',(s,))
        def position(pos,target=None,rotation=None):
            p.set_actor_location(u.Vector(*pos),False,True);p.character_movement.stop_movement_immediately()
            pc.set_control_rotation(rotation or u.MathLibrary.find_look_at_rotation(u.Vector(*pos)+u.Vector(0,0,64),u.Vector(*target)))
        if phase=='wait':
            if time.monotonic()-entered<6:return
            phase='position'
        if phase=='position':
            name=shots[index]
            if name=='spawn':position((400,1800,100),(1600,1800,164))
            if name=='note':position((600,1800,100),(800,1800,1))
            if name=='pattern-player':position((7550,5600,100),(7600,6085,480))
            if name=='pattern-camera':key('F1');key('Five');key('F1')
            if name=='pattern-player-same-view':
                camera=actors['OA_C2_Camera'];key('Q')
                # Disable gravity for this verification-only airborne pawn. Match camera eye exactly.
                p.character_movement.set_movement_mode(u.MovementMode.MOVE_FLYING)
                cp=camera.get_actor_location()
                current=p.get_actor_location(); eye=p.get_component_by_class(u.CameraComponent).get_world_location()
                offset=eye-current
                position((cp.x-offset.x,cp.y-offset.y,cp.z-offset.z),rotation=camera.get_actor_rotation())
            if name=='gm':
                p.character_movement.set_movement_mode(u.MovementMode.MOVE_WALKING)
                position((600,1800,100),(800,1800,1))
                entered=time.monotonic();phase='aim_note';return
            if name=='saved-b':
                key('Two');key('Three');entered=time.monotonic();phase='checkpoint';return
            if name=='dome':position((6600,3400,100),rotation=u.Rotator(pitch=65,yaw=25))
            entered=time.monotonic();phase='settle'
        elif phase=='aim_note' and time.monotonic()-entered>.5:
            key('E');key('F1');entered=time.monotonic();phase='memory'
        elif phase=='memory' and time.monotonic()-entered>5:
            phase='settle';entered=time.monotonic()
        elif phase=='checkpoint' and time.monotonic()-entered>.5:
            key('E');key('F1');phase='settle';entered=time.monotonic()
        elif phase=='settle' and time.monotonic()-entered>2.5:
            dest=OUT/('visual-'+shots[index]+'.png')
            dest.unlink(missing_ok=True)
            u.SystemLibrary.execute_console_command(world,'HighResShot 1600x900 filename="'+str(dest).replace('\\','/')+'"')
            phase='save';entered=time.monotonic()
        elif phase=='save' and time.monotonic()-entered>1.5:
            dest=OUT/('visual-'+shots[index]+'.png')
            if not dest.exists():raise RuntimeError('Missing screenshot '+str(dest))
            report['captures'].append(str(dest));index+=1
            if index==len(shots):finish();return
            phase='position'
    except Exception:finish(traceback.format_exc())
    finally:busy=False

assert LEVELS.load_level('/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout')
u.SystemLibrary.execute_console_command(UE.get_editor_world(),'MAP CHECK')
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
LEVELS.editor_request_begin_play()
