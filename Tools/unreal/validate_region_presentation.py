"""Step 5 rendered PIE: ordered dialogue and normal B-to-vista route, with recovery branches.
Reuses the real-projectile tutorial/puzzle helpers, never sends desktop keys.
"""
import sys,time,json
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent))
import validate_region_puzzle as q
q.OUT=Path(__file__).resolve().parents[2]/'Saved/RegionPresentation'
q.report={'status':'running','checks':[],'captures':[],'dialogue':[],'input':'Runtime input handlers; real projectiles and CharacterMovement; physical keys pending user'}
check=q.check;prop=q.prop;call=q.call;key=q.key;pos=q.pos;look=q.look

def shot(name,res='1600x900'):
    yield .25
    path=q.OUT/(name+'.png');path.unlink(missing_ok=True)
    u.SystemLibrary.execute_console_command(q.w,'HighResShot '+res+' filename="'+str(path).replace('\\','/')+'"')
    yield .4
    check('Capture '+name,path.exists());q.report['captures'].append(str(path))
    hud=q.pc.get_hud()
    q.report.setdefault('canvas_sizes',{})[name]=[hud.get_editor_property('CanvasWidth'),hud.get_editor_property('CanvasHeight')]

def walk(target):
    for _ in range(400):
        delta=target-q.p.get_actor_location();delta.z=0
        if delta.length()<55:break
        q.p.add_movement_input(delta.normal(),1,False);yield 0
    check('Walk to '+str(target),delta.length()<55,str(q.p.get_actor_location()))

def fresh_debug_saved():
    # Explicit GM fixture only for skip/death/device-loss branches. Normal route is tested first.
    q.L.editor_request_end_play();yield 1;q.L.editor_request_begin_play();yield 3;q.setup()
    yield from q.interact(q.actors['OA_RedNote'],(600,1800));yield 4
    key('F1');key('Two');key('Three');key('F1');yield .2;key('E');yield .3
    check('Fixture saved B',prop('CheckpointSaved'))

def run():
    assert q.L.load_level('/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout')
    for name in ['BP_RegionLoopDirector','BP_RegionHUD']:
        check(name+' compiles',u.BlueprintEditorLibrary.compile_blueprint(u.load_asset(q.BASE+name)))
    q.L.editor_request_begin_play();yield 3;q.setup()
    check('Presentation initializes',prop('Initialized') and not prop('FailureText'),prop('FailureText'))
    for _ in range(10):
        if prop('SubtitleText'):break
        yield .1
    check('Opening broadcast is one sentence',prop('SubtitleSpeaker')==1 and prop('SubtitleText').count('.')<=1,prop('SubtitleText'))
    yield from shot('ui-start')
    pos(10400,4400);yield .4;check('No vista before saved B',not prop('VistaActive') and prop('VistaPlayCount')==0)
    yield from q.interact(q.actors['OA_RedNote'],(600,1800));yield .3
    check('Memory overload clears dialogue',prop('SubtitleText')=='' and prop('DialogueQueueCount')==0)
    yield 4;yield from q.teaching()
    pos(6000,2900);yield .3
    observed=[];last=None;captured_host=False;captured_thought=False
    for _ in range(200):
        value=(prop('SubtitleSpeaker'),prop('SubtitleText'))
        if value[1] and value!=last:
            observed.append(value);q.report['dialogue'].append({'speaker':value[0],'text':value[1]});last=value
        if value[0]==1 and 'amber broadcast' in value[1] and not captured_host:
            yield from shot('ui-host');captured_host=True
        if value[0]==2 and not captured_thought:
            yield from shot('ui-inner-voice');captured_thought=True
        if captured_thought and prop('DialogueQueueCount')==0:break
        yield .1
    check('Host then inner doubt, never reversed',[a for a,b in observed]==[1,1,2,2],observed)
    check('Doubt refers to preceding broadcast',any('lethal' in text for speaker,text in observed if speaker==1)
        and any('before I commit' in text for speaker,text in observed if speaker==2))
    check('Queue stays bounded',prop('DialogueQueueCount')<=12)
    yield from q.interact(q.actors['OA_C2_Housing'],(7100,4100))
    camera=q.actors['OA_C2_Camera'];target=q.actors['OA_POI_T'].get_actor_location()
    desired=u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),target);current=camera.get_actor_rotation()
    call('PanTutorialCamera',float((desired.yaw-current.yaw)/.25),float((desired.pitch-current.pitch)/.25));yield 1
    check('Observation supplies inner voice',prop('PatternObserved'))
    yield from shot('ui-camera');key('Q');yield .2
    yield from q.tiles(457);yield from q.interact(q.actors['OA_PuzzleSubmitButton'],(6150,3370))
    check('Real puzzle opens D2',prop('PuzzleSolved') and not prop('DebugPrepared'))
    check('Old doubt is discarded on success','before I commit' not in prop('SubtitleText'))
    pos(8500,4400);yield from walk(u.Vector(9040,4400,100))
    check('Door passage alone does not play vista',not prop('VistaActive') and not prop('CheckpointSaved'))
    yield from q.interact(q.actors['OA_MemoryB_Case'],(9200,4400))
    check('B saved normally before cinematic',prop('CheckpointSaved') and not prop('DebugPrepared') and not prop('VistaActive'))
    yield from shot('ui-checkpoint')
    yield from walk(u.Vector(9900,4400,100))
    # Walk until trigger takes movement control; body stays on the safe platform.
    for _ in range(240):
        if prop('VistaActive'):break
        q.p.add_movement_input(u.Vector(1,0,0),1,False);yield 0
    check('Saved player walking onto platform starts vista',prop('VistaActive') and prop('VistaPlayCount')==1)
    body=q.p.get_actor_location();initialZ=prop('VistaCamera').get_actor_location().z
    check('Vista locks locomotion and switches viewpoint',q.pc.is_move_input_ignored())
    ammo=prop('Ammo');call('SetRegionFiring',True);key('R');yield .8
    check('Shooting blocked during vista',prop('Ammo')==ammo)
    yield from shot('vista-start');yield 2
    check('Camera rises and pulls back',prop('VistaCamera').get_actor_location().z>initialZ+300 and prop('VistaCamera').get_actor_location().x<10400)
    check('Body remains on platform',(q.p.get_actor_location()-body).length()<5)
    yield from shot('vista-mid');yield 1.4;yield from shot('vista-wide')
    check('Vista endpoint gives elevated overview',prop('VistaEnd').get_actor_location().z>=14000)
    check('Vista fills wide viewport without engine pillarboxes',not prop('VistaCamera').get_component_by_class(u.CameraComponent).get_editor_property('constrain_aspect_ratio'))
    yield from shot('vista-ultrawide','2560x1080');yield 4
    check('Normal end restores player view and controls',not prop('VistaActive') and q.pc.get_view_target()==q.p and not q.pc.is_move_input_ignored())
    check('Save and puzzle intact after vista',prop('CheckpointSaved') and prop('PuzzleSolved') and prop('HasGun') and prop('PuzzleMask')==457)
    yield from shot('ui-after-vista')
    yield 1;check('No retrigger while remaining on platform',prop('VistaPlayCount')==1)
    call('ApplyRegionDamage',10000.,prop('AttemptId'));yield 1
    check('Death after vista returns B without replay',prop('CheckpointSaved') and not prop('VistaActive') and prop('VistaPlayed') and q.p.get_actor_location().x>9000)
    pos(10400,4400);yield .3;check('Revisiting overlook does not replay',prop('VistaPlayCount')==1)
    # Rendered HighResShot sizes, not image resampling. Record the underlying PIE canvas
    # separately: it returns to the editor viewport size after each capture.
    for res in ['1280x720','2560x1440']:
        u.SystemLibrary.execute_console_command(q.w,'r.SetRes '+res+'w');yield 1
        yield from shot('ui-'+res,res)
    yield from fresh_debug_saved()
    pos(10400,4400);yield 1;key('SpaceBar');yield 1.2
    check('Space skips and restores control',not prop('VistaActive') and q.pc.get_view_target()==q.p and not q.pc.is_move_input_ignored())
    check('Skip preserves B and clears pending vista dialogue',prop('CheckpointSaved') and prop('DialogueQueueCount')==0)
    yield from fresh_debug_saved()
    pos(10400,4400);yield 1;old=prop('AttemptId');key('F1');key('One');yield 1
    check('GM death cancels vista once',prop('AttemptId')==old+1 and not prop('VistaActive') and prop('CheckpointSaved') and q.pc.get_view_target()==q.p)
    yield 8;check('Old cinematic timer cannot restart or move view',not prop('VistaActive') and q.pc.get_view_target()==q.p)
    yield from fresh_debug_saved()
    pos(10400,4400);yield 1;prop('VistaCamera').destroy_actor();yield .4
    check('Lost cinematic camera safely restores body',not prop('VistaActive') and q.pc.get_view_target()==q.p and not q.pc.is_move_input_ignored() and prop('CheckpointSaved'))
    q.L.editor_request_end_play();yield 1;q.L.editor_request_begin_play();yield 3;q.setup()
    check('New session clears cinematic and dialogue state',not prop('CheckpointSaved') and not prop('VistaPlayed') and prop('VistaPlayCount')==0 and prop('SubtitleSpeaker')==1)
    yield from q.interact(q.actors['OA_RedNote'],(600,1800));yield 4
    # Fast objective completion must remove outdated instructions from both current and queued lines.
    yield from q.interact(q.actors['OA_G2_Weapon'],(1270,1200));yield .2
    for a in q.guards():q.freeze(a)
    check('No red-note/gun-selection instructions after pickup','red note' not in prop('SubtitleText').lower() and 'Take the amber' not in prop('SubtitleText'))
    old=prop('AttemptId');call('RequestRegionDeath',old);yield .1
    check('Death flushes all queued speakers',prop('SubtitleText')=='' and prop('DialogueQueueCount')==0)
    yield 1
    check('New attempt inner voice does not resurrect old host',prop('SubtitleSpeaker')==2 and prop('AttemptId')==old+1)

    # User regression: re-enter C1 in one life, then repeat the whole teaching room after
    # an actual wrong-answer death. Experience is retained, access/door conditions are not.
    q.L.editor_request_end_play();yield 1;q.L.editor_request_begin_play();yield 3;q.setup()
    check('New session clears camera narrative memories',not prop('CameraLessonNarrated') and not prop('CardDiscoveryNarrated'))
    yield from q.interact(q.actors['OA_RedNote'],(600,1800));yield 4
    yield from q.teaching()
    check('First C1 completion records narrative experience',prop('CameraLessonNarrated') and prop('CardDiscoveryNarrated'))
    yield 16
    for turn in [60.,-60.,60.]:
        yield from q.interact(q.actors['OA_C1_Housing'],(4000,2350))
        check('Repeated C1 can still be controlled',prop('RemoteActive'))
        call('PanTutorialCamera',turn,0.);key('Q');yield .3
        check('Repeated C1 adds no dialogue',prop('SubtitleText')=='' and prop('DialogueQueueCount')==0)
    pos(6100,3800);yield .3
    yield from shot('puzzle-help-corner')
    yield from q.interact(q.actors['OA_PuzzleSubmitButton'],(6150,3370))
    check('Wrong puzzle answer triggers real penalty',prop('PuzzleSubmitting'))
    yield 2
    check('Death retains experience but resets access and C1 gate',prop('CameraLessonNarrated') and prop('CardDiscoveryNarrated')
        and not prop('HasAccessCard') and not prop('CameraLearned') and q.actors['OA_TutorialGate'].get_actor_enable_collision())
    yield from q.teaching()
    check('Retry still requires and completes normal C1 lesson',prop('CameraLearned') and not q.actors['OA_TutorialGate'].get_actor_enable_collision())
    check('Retry suppresses old card/lesson inner discovery',"point of view" not in prop('ThoughtText') and "maybe I can see" not in prop('ThoughtText'))
    check('Retry host guides current run without remembering death',"Follow the lights" in prop('HostText'))
    yield 12
    check('No old C1 dialogue remains queued after retry',prop('DialogueQueueCount')==0 and prop('SubtitleText')=='')

q.run=run
if __name__=='__main__':q.start()
