"""Step 5: incremental authored vista references; no room reconstruction or template edits."""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
import build_region_loop as region
import build_two_room_layout as layout
from graph_builder import compile_bp
OUT=ROOT/'Saved/RegionPresentation'
def build():
    OUT.mkdir(parents=True,exist_ok=True)
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem);actors_api=u.get_editor_subsystem(u.EditorActorSubsystem)
    assert levels.load_level(layout.MAP)
    actors={a.get_actor_label():a for a in actors_api.get_all_level_actors()}
    def add(cls,name,location):
        a=actors.get(name)
        if not a:
            a=actors_api.spawn_actor_from_class(cls,u.Vector(*location));a.set_actor_label(name)
            a.set_folder_path('OFFAIR_Region/Presentation');a.tags=['OFFAIR_REGION_STEP5'];actors[name]=a
        return a
    trigger=add(u.TriggerBox,'OA_VistaTrigger',(10400,4400,200))
    trigger.get_component_by_class(u.BoxComponent).set_box_extent(u.Vector(300,440,400),False)
    trigger.set_actor_enable_collision(False)
    focus=add(u.TargetPoint,'OA_VistaFocus',(23000,7000,350))
    camera=add(u.CameraActor,'OA_VistaCamera',(10400,4400,170))
    camera.camera_component.set_field_of_view(95.)
    # The HUD supplies horizontal letterboxing. Engine aspect locking would add side bars
    # in wide editor viewports, so this camera must fill the entire viewport.
    camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
    camera.camera_component.set_mobility(u.ComponentMobility.MOVABLE)
    actors['OA_POI_K2'].set_actor_location(u.Vector(-1000,1000,14500),False,True)
    focus.set_actor_location(u.Vector(24000,6500,4000),False,True)
    camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),focus.get_actor_location()),False)
    director=actors['OA_RegionLoopDirector']
    for k,v in dict(VistaCamera=camera,VistaTrigger=trigger,VistaStart=actors['OA_POI_K1'],
                   VistaEnd=actors['OA_POI_K2'],VistaFocus=focus).items():director.set_editor_property(k,v)
    for name in ['BP_RegionLoopDirector','BP_RegionHUD']:compile_bp(u.load_asset(region.BASE+'/'+name))
    assert levels.save_current_level()
    (OUT/'build-result.json').write_text(json.dumps({'status':'authored','map':layout.MAP,
        'vista_start':str(actors['OA_POI_K1'].get_actor_location()),'vista_end':str(actors['OA_POI_K2'].get_actor_location()),
        'focus':str(focus.get_actor_location()),'duration':8,'new_geometry':False},indent=2),encoding='utf-8')
    u.log('OFFAIR_REGION_PRESENTATION_AUTHORED')
if __name__=='__main__':build()
