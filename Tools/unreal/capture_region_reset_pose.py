"""Rendered regression frames: identical viewpoint before/after weapon reset.
No desktop input, no asset edits. Runtime handler calls, not physical-key claims.
"""
import json,time,traceback
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parents[2]/'Saved/RegionTutorialFixes'
L=u.get_editor_subsystem(u.LevelEditorSubsystem);UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
report={'status':'running','captures':[]};busy=False;wait=0.;started=time.monotonic();handle=None
d=p=pc=w=None;actors={}
def key(n):d.call_method('HandleRegionInput',(n,))
def pose():
    p.set_actor_location(u.Vector(400,1800,100),False,True)
    p.character_movement.stop_movement_immediately();pc.set_control_rotation(u.Rotator(pitch=-35,yaw=0))
def shot(name):
    yield 1.5
    path=OUT/('pose-'+name+'.png');path.unlink(missing_ok=True)
    u.SystemLibrary.execute_console_command(w,'HighResShot 1600x900 filename="'+str(path).replace('\\','/')+'"')
    yield 1
    assert path.exists(),name
    report['captures'].append(str(path))
def run():
    global d,p,pc,w,actors
    assert L.load_level('/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout')
    L.editor_request_begin_play();yield 5
    w=UE.get_game_world();d=u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,'/Game/OFFAIR/Region/BP_RegionLoopDirector.BP_RegionLoopDirector_C'))[0]
    p=u.GameplayStatics.get_player_character(w,0);pc=u.GameplayStatics.get_player_controller(w,0)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    def approach(target,position):
        p.set_actor_location(position,False,True);p.character_movement.stop_movement_immediately()
        eye=p.get_component_by_class(u.CameraComponent).get_world_location()
        pc.set_control_rotation(u.MathLibrary.find_look_at_rotation(eye,target.get_actor_bounds(False)[0]))
    pose();yield from shot('initial-unarmed')
    approach(actors['OA_RedNote'],u.Vector(600,1800,100));yield .3;key('E');yield 4.5
    for color,target,y in [('cyan','OA_G2_Weapon',1200),('amber','OA_G1_Weapon',2400)]:
        approach(actors[target],u.Vector(1270,y,100));yield .3;key('E');yield .2
        gs=u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,'/Game/OFFAIR/Region/BP_RegionGuard.BP_RegionGuard_C'))
        for a in gs:
            c=a.get_controller();c.get_component_by_class(u.BrainComponent).stop_logic('Pose capture');c.stop_movement();a.call_method('Stop Shooting',())
        pose();yield from shot(color+'-equipped')
        key('F1');key('One');yield 1;key('F1');pose();yield from shot(color+'-reset')
    # Amber victory text, delivered by the same health/death path; combat aim is tested separately.
    approach(actors['OA_G1_Weapon'],u.Vector(1270,2400,100));yield .3;key('E');yield .2
    for a in u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,'/Game/OFFAIR/Region/BP_RegionGuard.BP_RegionGuard_C')):
        u.GameplayStatics.apply_damage(a,10000,pc,p,u.DamageType)
    pose();yield from shot('amber-victory')
def finish(error=None):
    report.update(status='failed' if error else 'passed',error=error)
    (OUT/'pose-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    u.unregister_slate_post_tick_callback(handle);L.editor_request_end_play()
    u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
job=run()
def tick(dt):
    global busy,wait
    if busy:return
    busy=True
    try:
        if time.monotonic()-started>180:raise TimeoutError('Pose capture')
        wait-=dt
        if wait<=0:wait=next(job)
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
OUT.mkdir(parents=True,exist_ok=True)
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
