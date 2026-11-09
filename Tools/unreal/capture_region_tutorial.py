"""Offscreen rendered PIE frames for step 3. Does not touch desktop input or save assets."""
import json,time,traceback
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parents[2]/'Saved/RegionTutorial'
L=u.get_editor_subsystem(u.LevelEditorSubsystem);UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
report={'status':'running','captures':[]};busy=False;wait=0.;started=time.monotonic();handle=None
d=p=pc=w=None;actors={}
def key(n):d.call_method('HandleRegionInput',(n,))
def position(x,y,z=100,target=None,rotation=None):
    p.set_actor_location(u.Vector(x,y,z),False,True);p.character_movement.stop_movement_immediately()
    if target is not None:
        target=target.get_actor_bounds(False)[0] if isinstance(target,u.Actor) else target
        rotation=u.MathLibrary.find_look_at_rotation(p.get_component_by_class(u.CameraComponent).get_world_location(),target)
    if rotation:pc.set_control_rotation(rotation)
def shot(name):
    yield 1.5
    path=OUT/('visual-'+name+'.png');path.unlink(missing_ok=True)
    u.SystemLibrary.execute_console_command(w,'HighResShot 1600x900 filename="'+str(path).replace('\\','/')+'"')
    yield 1
    assert path.exists(),name
    report['captures'].append(str(path))
def run():
    global d,p,pc,w,actors
    assert L.load_level('/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout')
    L.editor_request_begin_play();yield 6
    w=UE.get_game_world();d=u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,'/Game/OFFAIR/Region/BP_RegionLoopDirector.BP_RegionLoopDirector_C'))[0]
    p=u.GameplayStatics.get_player_character(w,0);pc=u.GameplayStatics.get_player_controller(w,0)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    position(600,1800,target=actors['OA_RedNote']);yield from shot('note')
    key('E');yield 4.5
    position(1270,1200,target=actors['OA_G2_Weapon']);yield from shot('gun-choice')
    key('E');yield .3
    gs=u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,'/Game/OFFAIR/Region/BP_RegionGuard.BP_RegionGuard_C'))
    for a in gs:
        c=a.get_controller();c.get_component_by_class(u.BrainComponent).stop_logic('Capture fixture');c.stop_movement();a.call_method('Stop Shooting',())
    position(2300,1800,target=gs[0]);yield from shot('weapon-combat')
    for a in gs:u.GameplayStatics.apply_damage(a,10000,pc,p,u.DamageType)
    yield .5
    card=actors['OA_CameraAccessCard'];cp=card.get_actor_location();position(cp.x-180,cp.y,target=card);yield from shot('card')
    key('E');position(4000,2350,target=actors['OA_C1_Housing']);yield from shot('hack-prompt')
    key('E');yield from shot('c1')
    d.call_method('PanTutorialCamera',(60.,10.));key('Q')
    position(4500,1800,rotation=u.Rotator(yaw=0));yield from shot('opened-d1')
    key('F1');key('Seven');yield from shot('c2-initial')
    c2=actors['OA_C2_Camera'];desired=u.MathLibrary.find_look_at_rotation(c2.get_actor_location(),u.Vector(7600,6085,480));r=c2.get_actor_rotation()
    d.call_method('PanTutorialCamera',((desired.yaw-r.yaw)*4,(desired.pitch-r.pitch)*4));yield from shot('c2-found')
    key('Q');position(7550,5600,target=u.Vector(7600,6085,480));yield from shot('player-hidden-answer')
    key('F1');yield from shot('gm')
def finish(error=None):
    report.update(status='failed' if error else 'passed',error=error)
    (OUT/'visual-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    u.unregister_slate_post_tick_callback(handle);L.editor_request_end_play()
    u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
job=run()
def tick(dt):
    global busy,wait
    if busy:return
    busy=True
    try:
        if time.monotonic()-started>200:raise TimeoutError('Capture')
        wait-=dt
        if wait<=0:wait=next(job)
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
