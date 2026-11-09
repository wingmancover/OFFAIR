"""Narrative regression: host's current-run perspective and out-of-order puzzle discovery.
Uses real weapon/tile projectiles and normal interaction handlers; no physical desktop input.
"""
import sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent))
import validate_region_puzzle as q
q.OUT=Path(__file__).resolve().parents[2]/'Saved/NarrativeOrderFix'
q.report={'status':'running','checks':[],'dialogue':{},
          'input':'Normal teaching and real projectile input; runtime input handlers, no GM grants or physical keys'}

def listen(name,seconds=16):
    seen=[]
    for _ in range(int(seconds*10)):
        pair=[q.prop('SubtitleSpeaker'),q.prop('SubtitleText')]
        if pair[1] and (not seen or seen[-1]!=pair):seen.append(pair)
        yield .1
    q.report['dialogue'][name]=seen

def observe():
    yield from q.interact(q.actors['OA_C2_Housing'],(7100,4100))
    q.check('Normal input connects C2',q.prop('PuzzleRemote'))
    camera=q.actors['OA_C2_Camera'];target=q.actors['OA_POI_T'].get_actor_location()
    desired=u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),target);current=camera.get_actor_rotation()
    q.call('PanTutorialCamera',float((desired.yaw-current.yaw)/.25),float((desired.pitch-current.pitch)/.25));yield 1
    q.check('Camera still detects aligned pattern',q.prop('PatternAligned') and q.prop('PatternObserved'))

def run():
    assert q.L.load_level('/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout')
    for name in ['BP_RegionLoopDirector','BP_RegionHUD']:
        q.check(name+' compiles',u.BlueprintEditorLibrary.compile_blueprint(u.load_asset(q.BASE+name)))
    q.L.editor_request_begin_play();yield 3;q.setup()
    yield from q.interact(q.actors['OA_RedNote'],(600,1800));yield 4
    yield from q.teaching();yield from listen('first_C1')
    lines=q.report['dialogue']['first_C1']
    q.check('First lesson includes host and discovery',any(s==1 and 'Follow the lights' in t for s,t in lines)
        and any(s==2 and 'point of view' in t for s,t in lines))
    yield from q.interact(q.actors['OA_C1_Housing'],(4000,2350));q.call('PanTutorialCamera',60.,0.);q.key('Q');yield .3
    q.check('Same-life C1 revisit does not replay completed teaching',q.prop('SubtitleText')=='' and q.prop('DialogueQueueCount')==0)

    q.pos(6100,3800);yield .3;yield from q.tiles(457)
    q.check('Correct board entered before observing or submitting',q.prop('PuzzleMask')==457 and not q.prop('PatternObserved') and not q.prop('PuzzleSolved'))
    yield from observe()
    q.check('Already-filled answer gets confirmation instead of reproduce instruction','already entered' in q.prop('ThoughtText') and 'reproduce' not in q.prop('ThoughtText'))
    yield from listen('filled_before_observation',6)
    q.check('Confirmation actually appears on subtitle channel',any('already entered' in t for s,t in q.report['dialogue']['filled_before_observation']))
    q.key('Q');yield .2
    yield from q.interact(q.actors['OA_PuzzleClearButton'],(6150,3430));yield .2
    q.check('Clearing does not retain ready-to-submit narration','submit it now' not in q.prop('SubtitleText'))
    yield from q.interact(q.actors['OA_PuzzleSubmitButton'],(6150,3370));yield 2
    q.check('Actual wrong submission resets access but retains inner experience',not q.prop('HasAccessCard') and not q.prop('CameraLearned') and q.prop('CameraLessonNarrated'))
    yield from q.teaching()
    q.check('Retry restores host current-run completion line','Follow the lights' in q.prop('HostText'))
    yield from listen('retry_C1',10)
    lines=q.report['dialogue']['retry_C1']
    q.check('Retry host is visible, with no rediscovery inner voice',any(s==1 and 'Follow the lights' in t for s,t in lines)
        and not any(s==2 and ('point of view' in t or 'maybe I can see' in t) for s,t in lines))

    q.pos(6100,3800);yield .3;yield from q.tiles(457)
    yield from q.interact(q.actors['OA_PuzzleSubmitButton'],(6150,3370))
    q.check('Blind correct submit opens exit',q.prop('PuzzleSolved') and not q.prop('PatternObserved'))
    q.check('Blind success retains alternate host response','without my reference' in q.prop('HostText'))
    yield from observe()
    q.check('Post-solve observation does not overwrite progress narration','memory beyond the door' in q.prop('ThoughtText'))
    yield from listen('solved_before_observation',16)
    q.check('No pattern-use instructions after successful submission',not any('reproduce' in t or 'submit it now' in t or 'already entered' in t
        for s,t in q.report['dialogue']['solved_before_observation']))
    q.key('Q');yield .2
    q.check('Solved camera exit restores body with exit still open',q.pc.get_view_target()==q.p and not q.pc.is_move_input_ignored()
        and q.prop('PuzzleSolved') and not q.actors['OA_RegionExitGate'].get_actor_enable_collision())

    # The ordinary observe-first path must still provide the useful instruction.
    q.call('RequestRegionDeath',q.prop('AttemptId'));yield 1;yield from q.teaching()
    q.pos(6100,3800);yield .3;yield from observe()
    q.check('Observe-first still gives appropriate pattern instruction','reproduce' in q.prop('ThoughtText') and not q.prop('PuzzleSolved'))
    q.key('Q');yield .2;yield from q.tiles(457);yield .2
    q.check('Filling answer invalidates queued reproduce instruction','reproduce' not in q.prop('SubtitleText'))
    yield from listen('filled_after_observation',4)
    q.check('No stale reproduce sentence resumes after filling',not any('reproduce' in t for s,t in q.report['dialogue']['filled_after_observation']))
    q.check('Normal prerequisites used throughout',not q.prop('DebugPrepared'))

q.run=run
if __name__=='__main__':q.start()
