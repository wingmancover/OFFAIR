"""Background PIE integration checks. Invokes interaction commands after real view/LOS
checks; not a claim of physical keyboard/mouse verification. No assets saved."""
import json
import math
import time
import traceback
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/RegionLoop'
LEVELS=u.get_editor_subsystem(u.LevelEditorSubsystem)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
CLASS=u.load_class(None,'/Game/OFFAIR/Region/BP_RegionLoopDirector.BP_RegionLoopDirector_C')
REPORT={'status':'running','checks':[],'input_method':'HandleRegionInput through engine actor; view/range/LOS checked; physical keys pending user playtest'}
state='load'; busy=False; handle=None; elapsed=0.; since=0.; start=time.monotonic()
d=None; p=None; pc=None; actors={}; old_attempt=0; transient=None; original_camera=None; blocker=None; archived=None

def check(name,value,detail=None):
    REPORT['checks'].append({'name':name,'passed':bool(value),'detail':detail})
    if not value: raise AssertionError(name+': '+str(detail))
def prop(name): return d.get_editor_property(name)
def call(name,*args): return d.call_method(name,args)
def key(s): call('HandleRegionInput',s)
def pos(x,y,z=100): p.set_actor_location(u.Vector(x,y,z),False,True)
def look(a):
    eye=p.get_actor_location()+u.Vector(0,0,64)
    pc.set_control_rotation(u.MathLibrary.find_look_at_rotation(eye,a.get_actor_location()))
def go(s):
    global state,since
    state=s; since=elapsed
def finish(error=None):
    REPORT.update(status='failed' if error else 'passed',error=error,elapsed_seconds=round(time.monotonic()-start,2))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'validation-result.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
    if handle is not None: u.unregister_slate_post_tick_callback(handle)
    LEVELS.editor_request_end_play()
    u.EditorPythonScripting.set_keep_python_script_alive(False)
    u.SystemLibrary.quit_editor()

def step(dt):
    global d,p,pc,actors,elapsed,old_attempt,transient,original_camera,blocker,archived
    elapsed+=dt
    if time.monotonic()-start>240: raise TimeoutError(state)
    if state=='load':
        LEVELS.load_level('/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout')
        world=UE.get_editor_world()
        actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
        shell=actors['OA_Dome_Shell']
        check('Dome footprint halved',abs(shell.get_actor_scale3d().x/(1560*math.sqrt(.5))-1)<.001)
        check('Rooms and A unchanged',(actors['OA_StartA'].get_actor_location()-u.Vector(400,1800,100)).length()<1)
        for n in ['OA_TruePatternBack']+['OA_TrueFragment'+str(i) for i in range(5)]:
            a=actors[n]
            check(n+' restricted to C2 view',a.static_mesh_component.get_editor_property('only_owner_see') and a.get_owner()==actors['OA_C2_Camera'])
        for path in ['BP_RegionLoopDirector','BP_RegionHUD','BP_RegionCharacter','BP_RegionGameMode']:
            check(path+' compiles',u.BlueprintEditorLibrary.compile_blueprint(u.load_asset('/Game/OFFAIR/Region/'+path)))
        LEVELS.editor_request_begin_play(); go('wait')
    elif state=='wait':
        world=UE.get_game_world()
        if world is None: return
        ds=u.GameplayStatics.get_all_actors_of_class(world,CLASS)
        if not ds or not ds[0].get_editor_property('Initialized'): return
        d=ds[0]; p=u.GameplayStatics.get_player_character(world,0); pc=u.GameplayStatics.get_player_controller(world,0)
        actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
        check('Fresh session has no memory/save',not prop('MemoryExperienced') and not prop('CheckpointSaved') and prop('AttemptId')==1)
        check('GM hidden by default',not prop('GMOpen'))
        key('Two'); check('GM shortcuts disabled while hidden',not prop('HasGun'))
        key('F1'); key('Two'); check('GM prerequisite setup cannot skip first memory',not prop('HasGun'))
        key('F1')
        check('Progress cannot skip first memory',not call('ReportRegionProgress',prop('AttemptId'),0))
        # Checkpoint cannot be activated merely by teleporting around the closed gate.
        pos(9200,4380); look(actors['OA_MemoryB_Case']); go('b_rejected')
    elif state=='b_rejected' and elapsed-since>.15:
        key('E'); check('B rejects missing gameplay prerequisites',not prop('CheckpointSaved'))
        check('B explains missing prerequisites','locked' in prop('ThoughtText').lower(),prop('ThoughtText'))
        pos(400,1800); look(actors['OA_RedNote']); go('range')
    elif state=='range' and elapsed-since>.15:
        key('E'); check('Note outside 330cm does not collect',not prop('NoteCollected'))
        pos(600,1800); pc.set_control_rotation(u.Rotator(yaw=180)); go('away')
    elif state=='away' and elapsed-since>.15:
        key('E'); check('Looking away does not collect',not prop('NoteCollected'))
        blocker=u.OffairScriptTestLibrary.spawn_test_actor(UE.get_game_world(),u.StaticMeshActor)
        blocker.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
        blocker.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
        blocker.set_actor_scale3d(u.Vector(.3,1.5,1.5))
        blocker.set_actor_location(u.Vector(700,1800,80),False,True)
        look(actors['OA_RedNote']);go('occluded')
    elif state=='occluded' and elapsed-since>.15:
        key('E');check('Occluding wall prevents note interaction',not prop('NoteCollected'))
        blocker.destroy_actor();go('note')
    elif state=='note' and elapsed-since>.15:
        key('E'); check('E with aim and range starts memory event',prop('Transition')==1)
        check('Note parts hidden',all(a.get_editor_property('hidden') for a in prop('NoteParts')))
        check('Movement and look locked',pc.is_move_input_ignored() and pc.is_look_input_ignored())
        old_attempt=prop('AttemptId'); key('R'); key('E')
        check('Repeated input cannot interrupt or duplicate note death',prop('Transition')==1 and prop('AttemptId')==old_attempt)
        go('lock')
    elif state=='lock' and elapsed-since>1:
        check('Three-second memory wait not skipped',prop('Transition')==1)
        go('first_reset')
    elif state=='first_reset' and prop('Transition')==0:
        check('Exactly one first death',prop('DeathCount')==1 and prop('AttemptId')==2)
        check('First memory experience retained',prop('MemoryExperienced'))
        check('Note restored after regional reset',not prop('NoteCollected') and not actors['OA_RedNote'].get_editor_property('hidden'))
        check('Respawn at A',(p.get_actor_location()-u.Vector(400,1800,100)).length()<30)
        check('Input restored',not pc.is_move_input_ignored() and not pc.is_look_input_ignored())
        check('Death cue triggered once',prop('LoopSoundCount')==1)
        pos(600,1800);look(actors['OA_RedNote']);go('reread')
    elif state=='reread' and elapsed-since>.15:
        key('E');check('Reread collects without another forced death',prop('NoteCollected') and prop('Transition')==0)
        check('Optional note repeat no additional death',prop('DeathCount')==1)
        key('F1');key('Two');key('Four')
        check('Explicit GM setup grants all flags',prop('HasGun') and prop('HasAccessCard') and prop('CameraLearned') and prop('PuzzleSolved'))
        check('GM mutation changes world and puzzle',actors['OA_G1_Weapon'].get_editor_property('hidden') and prop('PuzzleMask')==21)
        world=UE.get_game_world()
        transient=u.OffairScriptTestLibrary.spawn_test_actor(world,u.Actor)
        check('Temporary actor registered',call('RegisterRegionTransient',transient,prop('AttemptId')))
        original_camera=actors['OA_C2_Camera'].get_actor_rotation()
        actors['OA_C2_Camera'].set_actor_rotation(u.Rotator(yaw=170),False)
        key('Five');check('Remote test preview entered',prop('RemoteActive'))
        old_attempt=prop('AttemptId');key('R')
        check('Remote death clears view immediately',not prop('RemoteActive') and pc.get_view_target()==p)
        check('Duplicate death rejected',not call('RequestRegionDeath',old_attempt))
        check('Late progress rejected',not call('ReportRegionProgress',old_attempt,3))
        go('second_reset')
    elif state=='second_reset' and prop('Transition')==0:
        check('Second reset clears unsaved inventory and puzzle',not any(prop(k) for k in ['HasGun','HasAccessCard','CameraLearned','PuzzleSolved','NoteCollected']) and prop('PuzzleMask')==0)
        check('Gun prop restored',not actors['OA_G1_Weapon'].get_editor_property('hidden'))
        gate=actors['OA_RegionExitGate']
        check('Exit gate baseline restored',not gate.get_editor_property('hidden') and gate.get_actor_enable_collision())
        restored=actors['OA_C2_Camera'].get_actor_rotation()
        check('Camera orientation baseline restored',max(abs(getattr(restored,k)-getattr(original_camera,k)) for k in ['pitch','yaw','roll'])<.1)
        check('Temporary actor cleaned up',not u.SystemLibrary.is_valid(transient))
        check('Old attempt remains invalid after reset',not call('ReportRegionProgress',old_attempt,0))
        check('Camera learning cannot bypass access card',not call('ReportRegionProgress',prop('AttemptId'),2))
        check('Access card cannot bypass weapon requirement',not call('ReportRegionProgress',prop('AttemptId'),1))
        stale=u.OffairScriptTestLibrary.spawn_test_actor(UE.get_game_world(),u.Actor)
        check('Late spawned actor rejected and destroyed',not call('RegisterRegionTransient',stale,old_attempt) and not u.SystemLibrary.is_valid(stale))
        archived=u.OffairScriptTestLibrary.spawn_test_actor(UE.get_game_world(),u.Actor)
        check('Current actor registered before B',call('RegisterRegionTransient',archived,prop('AttemptId')))
        key('F1') if not prop('GMOpen') else None
        key('Two');check('Can skip note after first death',prop('HasGun') and not prop('NoteCollected'))
        key('Three');go('save')
    elif state=='save' and elapsed-since>.15:
        check('Teleport alone does not save',not prop('CheckpointSaved'))
        key('E');check('E activates qualified B',prop('CheckpointSaved'))
        key('E');check('Save is idempotent',prop('SaveSoundCount')==1)
        check('B retains explicit debug provenance',prop('DebugPrepared'))
        old_attempt=prop('AttemptId')
        check('Completed region rejects late progression',not call('ReportRegionProgress',old_attempt,0))
        key('R');go('saved_reset')
    elif state=='saved_reset' and prop('Transition')==0:
        check('Post-B respawn uses B',(p.get_actor_location()-u.Vector(9250,4400,100)).length()<30)
        check('Saved inventory retained',prop('HasGun') and prop('HasAccessCard') and prop('CameraLearned'))
        check('Completed puzzle and door retained',prop('PuzzleSolved') and actors['OA_RegionExitGate'].get_editor_property('hidden') and not actors['OA_RegionExitGate'].get_actor_enable_collision())
        check('Completed region not reset (collected gun stays absent)',actors['OA_G1_Weapon'].get_editor_property('hidden'))
        check('Completed region spawned actors retained',u.SystemLibrary.is_valid(archived))
        check('Saved B health reset',prop('Health')==100)
        # Damage enters the same death pipeline as manual looping.
        call('ApplyRegionDamage',40.,prop('AttemptId'));check('Damage affects health',prop('Health')==60)
        u.GameplayStatics.apply_damage(p,70,pc,d,None)
        check('Real AnyDamage bridge requests death',prop('Transition')==2)
        go('damage_reset')
    elif state=='damage_reset' and prop('Transition')==0:
        check('Damage respawn restores saved player state',prop('Health')==100 and prop('CheckpointSaved'))
        bad=u.OffairScriptTestLibrary.spawn_test_actor(UE.get_game_world(),CLASS)
        bad.call_method('StepRegion',(0.1,))
        check('Missing refs fail closed without locking input',not bad.get_editor_property('Initialized') and bool(bad.get_editor_property('FailureText')) and not pc.is_move_input_ignored())
        bad.destroy_actor()
        LEVELS.editor_request_end_play();go('between')
    elif state=='between' and UE.get_game_world() is None:
        LEVELS.editor_request_begin_play();go('fresh')
    elif state=='fresh':
        w=UE.get_game_world()
        if w is None: return
        found=u.GameplayStatics.get_all_actors_of_class(w,CLASS)
        if not found or not found[0].get_editor_property('Initialized'): return
        d=found[0]
        check('Fresh PIE clears session save and memory',not prop('CheckpointSaved') and not prop('MemoryExperienced') and prop('DeathCount')==0)
        finish()

def tick(dt):
    global busy
    if busy:return
    busy=True
    try:step(dt)
    except Exception:finish(traceback.format_exc())
    finally:busy=False

u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
