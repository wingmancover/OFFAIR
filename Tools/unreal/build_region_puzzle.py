"""Step 4 incremental author. Preserves room geometry and user-adjusted props.
Run after managed-build, with the interactive editor on another map.
"""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
import build_region_loop as region
import build_two_room_layout as layout
from graph_builder import compile_bp
OUT=ROOT/'Saved/RegionPuzzle'
ASSETS=u.get_editor_subsystem(u.EditorAssetSubsystem)
ACTORS=u.get_editor_subsystem(u.EditorActorSubsystem)
LEVELS=u.get_editor_subsystem(u.LevelEditorSubsystem)

def build():
    OUT.mkdir(parents=True,exist_ok=True);region.OUT.mkdir(parents=True,exist_ok=True)
    assert LEVELS.load_level(layout.MAP)
    actors={a.get_actor_label():a for a in ACTORS.get_all_level_actors()}
    for name in ['metal','ivory','cyan_dim','cyan','amber','seam','green']:
        layout.MATS[name]=u.load_asset(layout.MAT_DIR+'/M_Lay_'+name)
    def box(name,pos,size,mat,collision=False):
        a=actors.get('OA_'+name)
        if not a:
            a=layout.box(name,pos,size,mat,collision,folder='POI_Props');actors['OA_'+name]=a
            a.tags=list(a.tags)+['OFFAIR_REGION_STEP4']
        return a
    def label(name,value,pos,yaw=180,size=16,color=(224,239,245)):
        a=actors.get('OA_'+name)
        if a:a.text_render.set_text(value)
        else:
            a=layout.text(name,value,pos,yaw,size,color);actors['OA_'+name]=a
        return a
    # Separate E targets keep clearing harmless and submission deliberate; no extra key binding.
    submit=box('PuzzleSubmitButton',(6380,3370,138),(5,38,47),'amber',True)
    clear=box('PuzzleClearButton',(6380,3430,138),(5,38,47),'cyan',True)
    actors['OA_PuzzleControls_Caption'].set_actor_hidden_in_game(True)
    label('PuzzleSubmitLabel','SUBMIT',(6376,3370,138),size=8,color=(255,220,135))
    label('PuzzleClearLabel','CLEAR',(6376,3430,138),size=8,color=(135,240,255))
    label('PuzzleWarning','WRONG SUBMISSION IS LETHAL',(6370,3400,205),size=12,color=(255,130,95))
    label('PanelHeader','SHOOT TO TOGGLE',(6570,3800,337),size=22)
    label('PuzzleInstructions','REPEAT A SHOT TO UNDO / E AT CONSOLE TO SUBMIT',(6570,3800,365),size=12)
    area=actors.get('OA_PuzzleArea')
    if not area:
        area=ACTORS.spawn_actor_from_class(u.TriggerBox,u.Vector(7000,4400,250))
        area.set_actor_label('OA_PuzzleArea');area.set_folder_path('OFFAIR_Region')
        area.get_component_by_class(u.BoxComponent).set_box_extent(u.Vector(1780,1780,500),False)
        area.set_actor_enable_collision(False)
    camera=actors['OA_C2_Camera']
    camera.camera_component.set_field_of_view(50.)
    # The grid is projected along rays from C2. Three physical depth planes form an L
    # from its optical position; rotation searches/framing, not moving the world pieces.
    eye=camera.get_actor_location(); center=u.Vector(7600,6085,500)
    actors['OA_POI_T'].set_actor_location(center,False,False)
    back=actors['OA_TruePatternBack']
    back.set_actor_location(u.Vector(7600,6100,500),False,False)
    back.set_actor_scale3d(u.Vector(3.1,.2,2.3))
    true_indices=[0,3,6,7,8]; pieces=[]
    for i in range(9):
        row,col=divmod(i,3);y=5825+row*85
        ratio=(y-eye.y)/(center.y-eye.y)
        target=u.Vector(center.x+(1-col)*65,center.y,center.z+(1-row)*65)
        p=eye+(target-eye)*ratio
        if i in true_indices:
            a=actors['OA_TrueFragment'+str(true_indices.index(i))]
            a.set_actor_location(p,False,False);a.set_actor_scale3d(u.Vector(.54*ratio,.05,.54*ratio))
            a.static_mesh_component.set_material(0,layout.MATS['cyan'])
        else:
            a=box('TruePatternEmpty'+str(i),(p.x,p.y,p.z),(54*ratio,5,54*ratio),'seam')
        pieces.append(a)
    for a in [back]+pieces:
        a.set_owner(camera);a.set_actor_enable_collision(False)
        c=a.static_mesh_component;c.set_only_owner_see(True);c.set_cast_shadow(False)
        c.set_editor_property('visible_in_reflection_captures',False)
        c.set_editor_property('visible_in_real_time_sky_captures',False)
    d=actors['OA_RegionLoopDirector'];tiles=[actors['OA_PuzzleTile_%d_%d'%(r,c)] for r in range(3) for c in range(3)]
    for a in tiles:
        a.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
        a.static_mesh_component.set_material(0,layout.MATS['ivory'])
        a.static_mesh_component.set_collision_profile_name('BlockAllDynamic')
        a.set_actor_enable_collision(True)
    baseline=list(d.get_editor_property('BaselineActors'))
    for a in [submit,clear,back,actors['OA_POI_T'],*pieces]:
        if a not in baseline:baseline.append(a)
        for c in a.get_components_by_class(u.SceneComponent):c.set_mobility(u.ComponentMobility.MOVABLE)
    for k,v in dict(PuzzleTiles=tiles,PuzzleCameraTarget=actors['OA_C2_Housing'],
        PuzzlePatternTarget=actors['OA_POI_T'],PuzzleSubmit=submit,PuzzleClear=clear,PuzzleArea=area,
        PuzzleOffMaterial=layout.MATS['ivory'],PuzzleOnMaterial=layout.MATS['cyan'],
        CorrectPatternMask=457,BroadcastPatternMask=151,BaselineActors=baseline,
        PuzzleSuccessSound=region.sound('S_PuzzleAccepted',[(550,.12),(825,.12),(1100,.25)]),
        PuzzleFailureSound=region.sound('S_PuzzleRejected',[(180,.18),(125,.3)])).items():d.set_editor_property(k,v)
    for name in ['BP_RegionLoopDirector','BP_RegionHUD']:
        bp=u.load_asset(region.BASE+'/'+name);compile_bp(bp)
        # Graphs/defaults are unchanged. New per-map references are serialized with the level;
        # compiling in memory avoids resaving shared assets held by the interactive editor.
    assert LEVELS.save_current_level()
    (OUT/'build-result.json').write_text(json.dumps({'status':'authored','tiles':9,'true_mask':457,
        'false_mask':151,'camera_fov':50,'camera_only_pieces':len(pieces),'map':layout.MAP},indent=2))
    u.log('OFFAIR_REGION_PUZZLE_AUTHORED')

if __name__=='__main__':build()
