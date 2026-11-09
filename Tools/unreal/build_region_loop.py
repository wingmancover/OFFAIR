"""Step 2 incremental authoring. Does not rebuild approved room geometry or legacy assets.

Run with UnrealEditor-Cmd -run=pythonscript -script=<this file>, while the main
editor is on another map. Managed code must be built before this script.
"""
import json
import math
from pathlib import Path
import struct
import sys
import wave
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import build_two_room_layout as layout
from graph_builder import Graph, create_bp, generated_class, pin, save

OUT = ROOT/'Saved/RegionLoop'
MAP = layout.MAP
MANAGED = '/Script/UnrealSharp.RegionLoopDirector_C'
BASE = '/Game/OFFAIR/Region'
LEVELS = u.get_editor_subsystem(u.LevelEditorSubsystem)
ACTORS = u.get_editor_subsystem(u.EditorActorSubsystem)
ASSETS = u.get_editor_subsystem(u.EditorAssetSubsystem)


def sound(name, notes):
    """Original procedural cue; deterministic mono PCM, no downloaded/licensed samples."""
    path = OUT/(name+'.wav')
    rate = 24000
    samples = []
    for freq, seconds in notes:
        for i in range(int(seconds*rate)):
            t = i/rate
            envelope = min(1,t/.015) * max(0,1-t/seconds)**2
            samples.append(int(10000*envelope*(math.sin(2*math.pi*freq*t)+.2*math.sin(4*math.pi*freq*t))))
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate)
        f.writeframes(struct.pack('<'+'h'*len(samples),*samples))
    asset_path=BASE+'/Audio/'+name
    if not ASSETS.does_asset_exist(asset_path):
        task=u.AssetImportTask()
        for k,v in dict(filename=str(path),destination_path=BASE+'/Audio',destination_name=name,
                        automated=True,save=True,replace_existing=False).items():
            task.set_editor_property(k,v)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return u.load_asset(asset_path)


def clear_events(bp):
    graph=u.BlueprintGraphEditor.get_graph_editor_by_name(bp,'EventGraph')
    graph.remove_nodes(graph.list_all_nodes())


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    assert u.load_class(None,MANAGED), 'Build managed code first'
    director_bp=create_bp(BASE+'/BP_RegionLoopDirector',MANAGED)
    clear_events(director_bp)
    g=Graph(director_bp,'EventGraph')
    ev=g.event('ReceiveTick')
    g.call(MANAGED+':StepRegion',Delta=pin(ev,'DeltaSeconds',True))
    cdo=u.get_default_object(generated_class(director_bp))
    tick=cdo.get_editor_property('primary_actor_tick')
    tick.set_editor_property('start_with_tick_enabled',True)
    cdo.set_editor_property('primary_actor_tick',tick)
    save(director_bp)
    hud_bp=create_bp(BASE+'/BP_RegionHUD','/Script/UnrealSharp.RegionHUD_C')
    save(hud_bp)
    player_bp=create_bp(BASE+'/BP_RegionCharacter','/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter.BP_FirstPersonCharacter_C')
    clear_events(player_bp)
    g=Graph(player_bp,'EventGraph')
    ev=g.event('ReceiveAnyDamage')
    director=g.engine('GameplayStatics','GetActorOfClass','ReturnValue',ActorClass=generated_class(director_bp))
    director=g.cast(director,generated_class(director_bp))
    g.guard(g.valid(director))
    attempt=g.get('AttemptId',director,MANAGED)
    g.call(MANAGED+':ApplyRegionDamage',self=director,Damage=pin(ev,'Damage',True),ExpectedAttempt=attempt)
    save(player_bp)
    mode=create_bp(BASE+'/BP_RegionGameMode','/Game/FirstPerson/Blueprints/BP_FirstPersonGameMode.BP_FirstPersonGameMode_C')
    m=u.get_default_object(generated_class(mode))
    m.set_editor_property('default_pawn_class',generated_class(player_bp))
    m.set_editor_property('hud_class',generated_class(hud_bp))
    save(mode)

    assert LEVELS.load_level(MAP)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    all_actors=ACTORS.get_all_level_actors()
    actors={a.get_actor_label():a for a in all_actors}
    # Exactly once: halve background footprint area; rooms and local platform stay fixed.
    shell=actors['OA_Dome_Shell']
    if 'OFFAIR_DOME_HALF_AREA' not in [str(t) for t in shell.tags]:
        factor=math.sqrt(.5)
        for a in all_actors:
            label=a.get_actor_label()
            if label.startswith('OA_Dome_') or label=='OA_Arena_Datum':
                p=a.get_actor_location()
                a.set_actor_location(u.Vector(p.x*factor,p.y*factor,p.z),False,False)
                s=a.get_actor_scale3d()
                # Horizontal footprint only; retain dome height and local landmark clearance.
                if label.startswith(('OA_Dome_Rib','OA_Dome_Ring')):
                    # Recompute compressed endpoint geometry, including oblique roof ribs.
                    delta=a.get_actor_forward_vector()*(s.x*100/2)
                    delta=u.Vector(delta.x*factor,delta.y*factor,delta.z)
                    rotation=u.MathLibrary.find_look_at_rotation(u.Vector(),delta)
                    a.set_actor_rotation(rotation,False)
                    a.set_actor_scale3d(u.Vector(delta.length()*2/100,s.y,s.z))
                else:
                    a.set_actor_scale3d(u.Vector(s.x*factor,s.y*factor,s.z))
        shell.tags=list(shell.tags)+['OFFAIR_DOME_HALF_AREA']

    # Use the original actor IDs/references, so moving props does not replace authored room geometry.
    camera=actors['OA_C2_Camera']
    # Place the optical viewpoint beyond the existing housing/lens rather than inside its mesh.
    camera.set_actor_location(u.Vector(7405,4345,324),False,False)
    camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),u.Vector(7600,6085,480)),False)
    board=actors['OA_TruePatternBack']
    board.set_actor_location(u.Vector(7600,6100,480),False,False)
    for i,(dx,dz) in enumerate([(-90,45),(-90,0),(-90,-45),(-30,-45),(30,-45)]):
        actors['OA_TrueFragment'+str(i)].set_actor_location(u.Vector(7600+dx,6085,480+dz),False,False)
    actors['OA_POI_T'].set_actor_location(u.Vector(7600,6085,480),False,False)
    for a in [board]+[actors['OA_TrueFragment'+str(i)] for i in range(5)]:
        a.set_owner(camera)
        a.static_mesh_component.set_only_owner_see(True)
        a.static_mesh_component.set_cast_shadow(False)
        a.static_mesh_component.set_editor_property('visible_in_reflection_captures',False)
        a.static_mesh_component.set_editor_property('visible_in_real_time_sky_captures',False)

    for name in ['metal','cyan_dim','ivory']:
        layout.MATS[name]=u.load_asset(layout.MAT_DIR+'/M_Lay_'+name)
    def added_box(name,pos,size,mat='metal'):
        if 'OA_'+name in actors: return actors['OA_'+name]
        a=layout.box(name,pos,size,mat,folder='POI_Props')
        a.tags=list(a.tags)+['OFFAIR_REGION_STEP2']
        actors['OA_'+name]=a
        return a
    # Inaccessible camera niche. Camera-only render ownership is the strict visibility guarantee,
    # with physical baffles providing a believable place for the hidden pattern.
    added_box('TruePatternCabinet',(7600,6040,200),(460,260,400))
    added_box('TruePatternHood',(7600,6035,620),(460,290,40))
    added_box('TruePatternLeft',(7380,6035,500),(30,290,240))
    added_box('TruePatternRight',(7820,6035,500),(30,290,240))
    gate=added_box('RegionExitGate',(8800,4400,250),(30,570,500),'ivory')
    # Static-to-movable only for runtime-reset participants; the architecture stays static.
    names=['OA_RedNote','OA_G1_Weapon','OA_G2_Weapon','OA_RegionExitGate','OA_C1_Camera','OA_C2_Camera']
    names += [n for n in actors if n.startswith(('OA_NoteWriting','OA_PuzzleTile','OA_TrueFragment'))]
    note_parts=[actors[n] for n in actors if n=='OA_RedNote' or n.startswith('OA_NoteWriting')]
    mutable=[actors[n] for n in names]
    for a in mutable:
        for comp in a.get_components_by_class(u.SceneComponent): comp.set_mobility(u.ComponentMobility.MOVABLE)
    # This actor is the session owner. A new PIE creates a fresh instance, so saves do not leak.
    old=[a for a in ACTORS.get_all_level_actors() if a.get_class()==generated_class(director_bp)]
    d=old[0] if old else ACTORS.spawn_actor_from_class(generated_class(director_bp),u.Vector(400,1800,0))
    d.set_actor_label('OA_RegionLoopDirector'); d.set_folder_path('OFFAIR_Region')
    b=actors.get('OA_RegionRespawnB')
    if not b:
        b=ACTORS.spawn_actor_from_class(u.TargetPoint,u.Vector(9250,4400,100))
        b.set_actor_label('OA_RegionRespawnB'); b.set_folder_path('OFFAIR_Region')
        b.tags=['OFFAIR_REGION_STEP2','CheckpointBSpawn']
    for k,v in dict(StartA=actors['OA_StartA'],StartB=b,Note=actors['OA_RedNote'],
                    CheckpointTerminal=actors['OA_MemoryB_Case'],ExitGate=gate,TestWeapon=actors['OA_G1_Weapon'],
                    PuzzleCamera=camera,BaselineActors=mutable,NoteParts=note_parts,
                    LoopSound=sound('S_RegionLoop',[(250,.15),(170,.18),(95,.32)]),
                    SaveSound=sound('S_MemorySaved',[(440,.14),(660,.16),(880,.3)])).items():
        d.set_editor_property(k,v)
    world.get_world_settings().set_editor_property('default_game_mode',generated_class(mode))
    assert LEVELS.save_current_level()
    (OUT/'build-result.json').write_text(json.dumps({'status':'authored','map':MAP,
        'blueprints':[bp.get_path_name() for bp in [director_bp,hud_bp,player_bp,mode]],
        'baseline_actors':len(mutable),'note_parts':len(note_parts),'dome_area_factor':.5,
        'true_pattern_camera_owner':camera.get_path_name()},indent=2),encoding='utf-8')
    u.log('OFFAIR_REGION_STEP2_AUTHORED')


if __name__=='__main__':
    build()
    # The current managed runtime requires the step-3 references and template adapters.
    # Reapply them after rebuilding foundations, rather than silently reverting gameplay.
    import build_region_tutorial
    build_region_tutorial.build()
