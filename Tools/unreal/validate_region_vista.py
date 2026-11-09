"""Focused rendered framing check after camera-only edits; explicit GM setup, not progression proof."""
import sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent))
import validate_region_presentation as presentation
q=presentation.q
q.OUT=Path(__file__).resolve().parents[2]/'Saved/PresentationFix/Vista'
q.report={'status':'running','checks':[],'captures':[],
          'input':'Explicit GM fixture for final authored camera framing; no physical keys'}

def run():
    assert q.L.load_level('/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout')
    q.L.editor_request_begin_play();yield 3;q.setup()
    yield from q.interact(q.actors['OA_RedNote'],(600,1800));yield 4
    q.key('F1');q.key('Two');q.key('Three');q.key('F1');yield .2;q.key('E');yield .3
    q.check('B fixture explicitly saved',q.prop('CheckpointSaved'))
    q.pos(10400,4400);yield .2
    q.check('Authored vista starts',q.prop('VistaActive'))
    camera=q.prop('VistaCamera');component=camera.get_component_by_class(u.CameraComponent)
    q.check('No camera aspect lock',not component.get_editor_property('constrain_aspect_ratio'))
    q.check('Wider overview lens',abs(component.get_editor_property('field_of_view')-95)<.01)
    yield 5
    q.check('Final camera is high and behind both rooms',camera.get_actor_location().z>=14499 and camera.get_actor_location().x<=-999)
    yield from presentation.shot('vista-final-16x9','1600x900')
    yield from presentation.shot('vista-final-wide','2560x1080')
    yield 3
    q.check('Returns to body with controls restored',not q.prop('VistaActive') and q.pc.get_view_target()==q.p and not q.pc.is_move_input_ignored())
    q.check('Memory and weapon preserved',q.prop('CheckpointSaved') and q.prop('HasGun'))

q.run=run
if __name__=='__main__':q.start()
