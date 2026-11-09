"""Step 4 PIE regression, real projectiles + runtime input handlers; no OS input.
Rendered offscreen for visual evidence. No GM prerequisites on the normal route.
"""
import json,time,traceback
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parents[2]/'Saved/RegionPuzzle'
L=u.get_editor_subsystem(u.LevelEditorSubsystem); UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
BASE='/Game/OFFAIR/Region/'
report={'status':'running','checks':[],'captures':[],'input':'Runtime handlers; real projectile collision; no physical keyboard/mouse'}
busy=False;handle=None;wait=0.;started=time.monotonic();d=p=pc=w=None;actors={}
def check(n,v,detail=None):
    report['checks'].append(dict(name=n,passed=bool(v),detail=detail))
    (OUT/'puzzle-progress.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if not v:raise AssertionError(n+': '+str(detail))
def prop(n):return d.get_editor_property(n)
def call(n,*a):return d.call_method(n,a)
def key(n):call('HandleRegionInput',n)
def pos(x,y,z=100):p.set_actor_location(u.Vector(x,y,z),False,True);p.character_movement.stop_movement_immediately()
def look(a):
    target=a.get_actor_bounds(False)[0] if isinstance(a,u.Actor) else a
    eye=p.get_component_by_class(u.CameraComponent).get_world_location()
    pc.set_control_rotation(u.MathLibrary.find_look_at_rotation(eye,target))
def guards():return [a for a in u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,BASE+'BP_RegionGuard.BP_RegionGuard_C')) if a.get_editor_property('Current HP')>0]
def freeze(a):
    c=a.get_controller()
    if c:
        c.get_component_by_class(u.BrainComponent).stop_logic('Deterministic aim fixture');c.stop_movement()
    a.call_method('Stop Shooting',());a.character_movement.stop_movement_immediately()
def fire(a):
    look(a);yield .2;call('SetRegionFiring',True);yield .12;call('SetRegionFiring',False);yield .45
def interact(a,xyz):
    pos(*xyz);look(a);yield .25;key('E');yield .15
def shot(name):
    yield .8
    path=OUT/(name+'.png');path.unlink(missing_ok=True)
    u.SystemLibrary.execute_console_command(w,'HighResShot 1600x900 filename="'+str(path).replace('\\','/')+'"')
    yield .7;check('Capture '+name,path.exists());report['captures'].append(str(path))
def setup():
    global d,p,pc,w,actors
    w=UE.get_game_world();d=u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,BASE+'BP_RegionLoopDirector.BP_RegionLoopDirector_C'))[0]
    p=u.GameplayStatics.get_player_character(w,0);pc=u.GameplayStatics.get_player_controller(w,0)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
def teaching():
    yield from interact(actors['OA_G2_Weapon'],(1270,1200))
    gs=guards();check('Cyan encounter has two guards',len(gs)==2)
    for a in gs:freeze(a)
    pos(2600,1800)
    for idx,a in enumerate(gs):
        a.set_actor_location(u.Vector(3100,1800+idx*220,100),False,True)
        for _ in range(6):
            if a.get_editor_property('Current HP')<=0:break
            yield from fire(a)
        check('Actual shots defeat guard '+str(idx),a.get_editor_property('Current HP')<=0)
    yield .3;check('Real clear drops access card',prop('CardDropped') and prop('LivingGuards')==0)
    card=actors['OA_CameraAccessCard'];cp=card.get_actor_location()
    yield from interact(card,(cp.x-200,cp.y))
    check('Card collected by E',prop('HasAccessCard'))
    yield from interact(actors['OA_C1_Housing'],(4000,2350))
    call('PanTutorialCamera',60.,20.);key('Q');yield .2
    check('C1 normal lesson opens D1',prop('CameraLearned') and not actors['OA_TutorialGate'].get_actor_enable_collision())
def tiles(mask):
    pos(6100,3800)
    for i in range(9):
        if mask&(1<<i):yield from fire(actors['OA_PuzzleTile_%d_%d'%divmod(i,3)])
def run():
    assert L.load_level('/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout')
    for name in ['BP_RegionLoopDirector','BP_RegionHUD','BP_RegionBullet']:
        check(name+' compiles',u.BlueprintEditorLibrary.compile_blueprint(u.load_asset(BASE+name)))
    L.editor_request_begin_play();yield 4;setup()
    check('Puzzle configuration initializes',prop('Initialized') and not prop('FailureText'),prop('FailureText'))
    yield from interact(actors['OA_C2_Housing'],(7100,4100))
    check('No card cannot hack C2',not prop('RemoteActive'))
    yield from interact(actors['OA_PuzzleSubmitButton'],(6150,3370))
    check('No prerequisites cannot submit',prop('PuzzleSubmitCount')==0 and prop('DeathCount')==0)
    yield from interact(actors['OA_RedNote'],(600,1800));yield 4
    check('First memory loop occurred',prop('MemoryExperienced') and prop('DeathCount')==1)
    yield from teaching()
    pos(6000,2900);yield .3
    check('Room host recommends broadcast reference','broadcast' in prop('HostText').lower())
    pos(6100,4000);look(actors['OA_FalsePatternFrame']);yield from shot('puzzle-broadcast')
    yield from tiles(1)
    check('Real bullet toggles top-left on',prop('PuzzleMask')==1,prop('PuzzleMask'))
    yield from tiles(1)
    check('Second bullet toggles same tile off',prop('PuzzleMask')==0,prop('PuzzleMask'))
    yield from tiles(16)
    yield from interact(actors['OA_PuzzleClearButton'],(6150,3430))
    check('Clear is safe and empties board',prop('PuzzleMask')==0 and prop('DeathCount')==1)
    # Deliberate repeated callback fixture; actual shot-to-tile behavior is checked above.
    duplicate=u.OffairScriptTestLibrary.spawn_test_actor(w,u.TargetPoint)
    check('Register fixture with current player',call('RegisterTutorialProjectile',duplicate,p))
    hit=u.HitResult();target_tile=actors['OA_PuzzleTile_1_1']
    call('OnPuzzleProjectileHit',duplicate,target_tile,u.Vector(),hit)
    call('OnPuzzleProjectileHit',duplicate,target_tile,u.Vector(),hit)
    check('Duplicate hit toggles only once',prop('PuzzleMask')==16)
    yield from interact(actors['OA_PuzzleClearButton'],(6150,3430))
    yield from tiles(151);check('Actual shots reproduce false T',prop('PuzzleMask')==151,prop('PuzzleMask'))
    pos(6100,3800);look(actors['OA_PuzzlePanelFrame']);yield from shot('puzzle-false-input')
    count=prop('PuzzleSubmitCount');attempt=prop('AttemptId')
    yield from interact(actors['OA_PuzzleSubmitButton'],(6150,3370))
    check('Wrong submit locks with explicit feedback',prop('PuzzleSubmitting') and pc.is_move_input_ignored())
    key('E');key('Q');key('R');call('SetRegionFiring',True)
    check('Repeated input cannot cancel lethal result',prop('PuzzleSubmitting') and prop('PuzzleSubmitCount')==count+1 and pc.is_move_input_ignored())
    yield 2
    check('Wrong answer causes exactly one loop to A',prop('AttemptId')==attempt+1 and prop('DeathCount')==2 and p.get_actor_location().x<600)
    check('Puzzle death restores room baseline',prop('PuzzleMask')==0 and not prop('HasGun') and not prop('HasAccessCard') and not prop('CameraLearned') and not prop('PuzzleSolved') and actors['OA_RegionExitGate'].get_actor_enable_collision())
    check('Only experience retained',prop('MemoryExperienced') and prop('PuzzleFailedBefore') and not prop('PatternObserved'))
    check('All tile materials reset to off',all(a.static_mesh_component.get_material(0)==prop('PuzzleOffMaterial') for a in prop('PuzzleTiles')))
    check('C2 initial orientation restored',abs(actors['OA_C2_Camera'].get_actor_rotation().yaw-20)<.1)
    yield 3.5
    check('No delayed second death',prop('AttemptId')==attempt+1)
    yield from teaching()
    yield from interact(actors['OA_C2_Housing'],(5000,4100))
    check('C2 out of range rejected',not prop('RemoteActive'))
    blocker=u.OffairScriptTestLibrary.spawn_test_actor(w,u.StaticMeshActor)
    blocker.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
    blocker.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
    blocker.set_actor_scale3d(u.Vector(.5,5,6));blocker.set_actor_location(u.Vector(7250,4200,250),False,True)
    yield from interact(actors['OA_C2_Housing'],(7100,4100))
    check('C2 occlusion rejected',not prop('RemoteActive'));blocker.destroy_actor()
    yield from interact(actors['OA_C2_Housing'],(7100,4100))
    check('Aim/E enters C2',prop('RemoteActive') and prop('PuzzleRemote'))
    check('Camera starts away from answer',not prop('PatternObserved') and not prop('PatternAligned'))
    yield from shot('puzzle-camera-initial')
    camera=actors['OA_C2_Camera'];target=actors['OA_POI_T'].get_actor_location()
    desired=u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),target);current=camera.get_actor_rotation()
    call('PanTutorialCamera',float((desired.yaw-current.yaw)/.25),float((desired.pitch-current.pitch)/.25));yield 1
    check('Panning centers and identifies pattern',prop('PatternAligned') and prop('PatternObserved'))
    check('Camera observation alone does not solve',not prop('PuzzleSolved') and prop('PuzzleMask')==0)
    yield from shot('puzzle-camera-aligned')
    key('Q');yield .2;check('C2 exit restores view and controls',not prop('RemoteActive') and pc.get_view_target()==p and not pc.is_move_input_ignored())
    pos(7600,5650);look(target);yield from shot('puzzle-body-hidden-answer')
    check('Answer meshes restricted to C2 ownership',all(actors['OA_TrueFragment'+str(i)].get_owner()==camera and actors['OA_TrueFragment'+str(i)].static_mesh_component.get_editor_property('only_owner_see') for i in range(5)))
    yield from tiles(457);check('Actual shots reproduce correct L',prop('PuzzleMask')==457,prop('PuzzleMask'))
    yield from interact(actors['OA_PuzzleSubmitButton'],(6150,3370))
    check('Correct submit opens D2 while alive',prop('PuzzleSolved') and not actors['OA_RegionExitGate'].get_actor_enable_collision() and prop('DeathCount')==2)
    check('Host reacts to independent camera answer','Ignoring my instructions' in prop('HostText'))
    yield from shot('puzzle-success')
    key('E');check('Solved submit cannot repeat reward',prop('PuzzleSubmitCount')==2)
    yield from tiles(1);check('Solved board cannot change',prop('PuzzleMask')==457)
    yield 2
    check('Success banner clears instead of blocking view',prop('PuzzleStatus')=='')
    check('No GM prerequisites used',not prop('DebugPrepared') and not prop('GMOpen'))
    pos(8500,4400)
    for _ in range(300):
        delta=u.Vector(9040,4400,100)-p.get_actor_location();delta.z=0
        if delta.length()<65:break
        p.add_movement_input(delta.normal(),1,False);yield 0
    check('Character walks through opened D2',p.get_actor_location().x>8950)
    check('Crossing D2 does not silently save',not prop('CheckpointSaved'))
    yield from interact(actors['OA_MemoryB_Case'],(9200,4400))
    check('Normal route saves B with E',prop('CheckpointSaved') and not prop('DebugPrepared'))
    yield from shot('puzzle-checkpoint-b')
    old=prop('AttemptId');call('ApplyRegionDamage',10000.,old);yield 1
    check('B death preserves puzzle and equipment',prop('CheckpointSaved') and prop('PuzzleMask')==457 and prop('PuzzleSolved') and prop('HasGun') and len(p.get_editor_property('Owned Weapons'))==1 and p.get_actor_location().x>9000)
    check('Completed camera direction retained',abs(camera.get_actor_rotation().yaw-desired.yaw)<.1)
    L.editor_request_end_play();yield 1;L.editor_request_begin_play();yield 3;setup()
    check('Fresh PIE clears puzzle memories and save',not prop('CheckpointSaved') and not prop('PuzzleFailedBefore') and prop('PuzzleMask')==0)
    # Repeat the normal route with no C2 observation: knowledge must not become an artificial ability gate.
    yield from interact(actors['OA_RedNote'],(600,1800));yield 4;yield from teaching()
    yield from tiles(457);yield from interact(actors['OA_PuzzleSubmitButton'],(6150,3370))
    check('Known correct answer accepted without C2 visit',prop('PuzzleSolved') and not prop('PatternObserved') and not prop('DebugPrepared'))
    check('Direct solution has alternate host line','without my reference' in prop('HostText'))
    old=prop('AttemptId');call('RequestRegionDeath',old);yield 1
    check('Solved but unsaved puzzle resets',not prop('PuzzleSolved') and prop('PuzzleMask')==0 and actors['OA_RegionExitGate'].get_actor_enable_collision())
    key('F1');key('Seven');yield .2
    check('GM C2 entry cannot grant card or lesson',prop('RemoteActive') and not prop('HasAccessCard') and not prop('CameraLearned'))
    call('ApplyRegionDamage',10000.,prop('AttemptId'));yield 1
    check('C2 death restores body',not prop('RemoteActive') and pc.get_view_target()==p and not pc.is_move_input_ignored())
    if not prop('GMOpen'):key('F1')
    key('Seven');actors['OA_C2_Camera'].destroy_actor();yield .3
    check('Destroyed C2 exits without completion',not prop('RemoteActive') and pc.get_view_target()==p and not prop('PuzzleSolved'))
    call('RequestRegionDeath',prop('AttemptId'));yield 1
    check('Missing baseline fails closed',prop('Transition')==2 and 'baseline' in prop('FailureText').lower())
    L.editor_request_end_play();yield 1;L.editor_request_begin_play();yield 3;setup()
    yield from interact(actors['OA_RedNote'],(600,1800));yield 4;yield from teaching()
    yield from interact(actors['OA_PuzzleSubmitButton'],(6150,3370))
    check('Empty submission is an explicit wrong answer',prop('PuzzleSubmitting') and not prop('PuzzleSolved'))
    old=prop('AttemptId');key('F1');key('One');yield 3
    check('GM death cancels pending result timer',prop('AttemptId')==old+1 and prop('Transition')==0 and not prop('PuzzleSubmitting'))

def finish(error=None):
    report.update(status='failed' if error else 'passed',error=error,seconds=round(time.monotonic()-started,2))
    (OUT/'puzzle-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    u.unregister_slate_post_tick_callback(handle);L.editor_request_end_play()
    u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
job=None
def tick(dt):
    global busy,wait
    if busy:return
    busy=True
    try:
        if time.monotonic()-started>360:raise TimeoutError('Puzzle verification')
        wait-=dt
        if wait<=0:wait=next(job)
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
def start():
    global job,handle,started
    started=time.monotonic();job=run()
    OUT.mkdir(parents=True,exist_ok=True)
    u.EditorPythonScripting.set_keep_python_script_alive(True)
    handle=u.register_slate_post_tick_callback(tick)
if __name__=='__main__':start()
