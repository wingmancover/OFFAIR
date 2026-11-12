"""OFFAIR title and default-map validation. Normal projectile route first; explicit GM fixtures for interrupts.
No packaging, no OS keyboard/mouse input, no project asset saves.
"""
import sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent))
import validate_region_presentation as presentation
q=presentation.q
q.OUT=Path(__file__).resolve().parents[2]/'Saved/OffairTitleA'
q.report={'status':'running','checks':[],'captures':[],
          'input':'Normal E/shot handlers and CharacterMovement; explicit GM interruption fixtures; physical keys pending user'}
check=q.check;prop=q.prop;key=q.key;call=q.call

def await_title():
    for _ in range(200):
        if prop('TitleActive'):break
        yield .05
    check('Title starts after completed return',prop('TitleActive') and not prop('VistaActive') and q.pc.get_view_target()==q.p)

def run():
    settings=u.get_default_object(u.GameMapsSettings)
    expected='/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout'
    editor_map=settings.get_editor_property('editor_startup_map').export_text()
    game_map=settings.get_editor_property('game_default_map').export_text()
    check('Persisted editor default uses new map',expected in str(editor_map),str(editor_map))
    check('Persisted game default uses new map',expected in str(game_map),str(game_map))
    packages=u.load_object(None,'/Script/DeveloperToolSettings.Default__ProjectPackagingSettings').get_editor_property('MapsToCook')
    check('Cook list contains new map only',[p.file_path for p in packages]==[expected])
    check('Fresh editor automatically opened new map',q.UE.get_editor_world().get_path_name().startswith(expected+'.'))
    check('Old map asset remains',u.EditorAssetLibrary.does_asset_exist('/Game/OFFAIR/Levels/Lvl_Prototype'))
    for name in ['BP_RegionLoopDirector','BP_RegionHUD']:
        check(name+' compiles',u.BlueprintEditorLibrary.compile_blueprint(u.load_asset(q.BASE+name)))
    q.L.editor_request_begin_play();yield 3;q.setup()
    check('New map starts region gameplay',prop('Initialized') and not prop('FailureText'))
    font=q.pc.get_hud().get_editor_property('TitleFont')
    check('HUD serializes runtime bold title font',font is not None and str(font.get_editor_property('legacy_font_name'))=='Bold'
        and font.get_editor_property('font_cache_type')==u.FontCacheType.RUNTIME)
    texture=q.pc.get_hud().get_editor_property('TitleWordmark')
    check('A wordmark is serialized at full source resolution',texture is not None and texture.blueprint_get_size_x()==6400 and texture.blueprint_get_size_y()==1200)
    check('Wordmark keeps lossless UI alpha without streaming or mips',
          texture.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_EDITOR_ICON
          and texture.get_editor_property('lod_group')==u.TextureGroup.TEXTUREGROUP_UI
          and texture.get_editor_property('mip_gen_settings')==u.TextureMipGenSettings.TMGS_NO_MIPMAPS
          and texture.get_editor_property('never_stream')
          and texture.get_editor_property('address_x')==u.TextureAddress.TA_CLAMP
          and texture.get_editor_property('address_y')==u.TextureAddress.TA_CLAMP)
    check('Title is absent at spawn',not prop('TitleActive') and not prop('TitlePlayed') and prop('TitlePlayCount')==0)
    yield from q.interact(q.actors['OA_RedNote'],(600,1800));yield 4;yield from q.teaching()
    yield from q.interact(q.actors['OA_C2_Housing'],(7100,4100))
    camera=q.actors['OA_C2_Camera'];target=q.actors['OA_POI_T'].get_actor_location()
    desired=u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),target);current=camera.get_actor_rotation()
    call('PanTutorialCamera',float((desired.yaw-current.yaw)/.25),float((desired.pitch-current.pitch)/.25));yield 1;key('Q');yield .2
    yield from q.tiles(457);yield from q.interact(q.actors['OA_PuzzleSubmitButton'],(6150,3370))
    yield from q.interact(q.actors['OA_MemoryB_Case'],(9200,4400))
    check('B saved by normal teaching and puzzle route',prop('CheckpointSaved') and not prop('DebugPrepared'))
    check('Saving alone does not show title',not prop('TitleActive') and not prop('TitlePlayed'))
    yield from presentation.walk(u.Vector(9900,4400,100))
    for _ in range(240):
        if prop('VistaActive'):break
        q.p.add_movement_input(u.Vector(1,0,0),1,False);yield 0
    check('Normal walk starts cinematic without title',prop('VistaActive') and not prop('TitleActive'))
    yield 4.8
    check('Title absent while cinematic runs',not prop('TitleActive'))
    # Explicit reading-time fixture: keep the existing legitimate inner line alive through the return,
    # so pause/resume is tested even though ordinary vista dialogue usually finishes before 8 seconds.
    check('Legitimate vista subtitle available for timing fixture',bool(prop('SubtitleText')))
    q.d.set_editor_property('SubtitleRemaining',6.)
    yield from await_title()
    started=u.GameplayStatics.get_time_seconds(q.w);frozen=prop('SubtitleRemaining');sentence=prop('SubtitleText')
    check('Title restores move and look input',not q.pc.is_move_input_ignored() and not q.pc.is_look_input_ignored())
    check('Title has three seconds and one-shot state',2.9<=prop('TitleRemaining')<=3 and prop('TitlePlayed') and prop('TitlePlayCount')==1)
    yield from presentation.shot('offair-title-a-16x9')
    before=q.p.get_actor_location()
    movement_start=u.GameplayStatics.get_time_seconds(q.w)
    for _ in range(600):
        if u.GameplayStatics.get_time_seconds(q.w)-movement_start>=.35:break
        q.p.add_movement_input(u.Vector(-1,0,0),1,False);yield 0
    distance=(q.p.get_actor_location()-before).length()
    check('Player moves during title',prop('TitleActive') and distance>10,{'distance_cm':distance,'seconds':u.GameplayStatics.get_time_seconds(q.w)-movement_start})
    ammo=prop('Ammo');call('SetRegionFiring',True);yield .2;call('SetRegionFiring',False)
    check('Firing remains available during title',prop('Ammo')<ammo)
    check('Subtitle clock and text paused during title',abs(prop('SubtitleRemaining')-frozen)<.01 and prop('SubtitleText')==sentence)
    yield from presentation.shot('offair-title-a-wide','2560x1080')
    for _ in range(80):
        if not prop('TitleActive'):break
        yield .05
    elapsed=u.GameplayStatics.get_time_seconds(q.w)-started
    check('Title ends at three seconds without a second phase',not prop('TitleActive') and prop('TitleRemaining')==0 and 2.9<=elapsed<=3.15,elapsed)
    yield .3
    check('Subtitle resumes its remaining reading time',prop('SubtitleText')==sentence and prop('SubtitleRemaining')<frozen)
    yield from presentation.shot('offair-title-a-hud-restored')
    q.pos(10400,4400);yield .3
    check('Returning to platform does not replay title',not prop('TitleActive') and prop('TitlePlayCount')==1)

    yield from presentation.fresh_debug_saved()
    q.pos(10400,4400);yield 1;key('SpaceBar');yield .2
    check('Skip return blend does not show title early',prop('VistaActive') and not prop('TitleActive'))
    yield from await_title()
    check('Skipping still shows one title',prop('TitlePlayCount')==1)
    yield from presentation.shot('offair-title-a-4k','3840x2160')
    key('E');key('Q');key('SpaceBar');yield .2
    check('Repeated gameplay input cannot restart title',prop('TitlePlayCount')==1 and prop('TitleRemaining')<2.9)
    key('F1');key('One');yield .1
    check('Death immediately clears active title',not prop('TitleActive') and prop('TitleRemaining')==0)
    yield 1;q.pos(10400,4400);yield 3.2
    check('Death retains B and never replays used title',prop('CheckpointSaved') and prop('TitlePlayed') and prop('TitlePlayCount')==1 and not prop('TitleActive'))

    yield from presentation.fresh_debug_saved()
    q.pos(10400,4400);yield 1;call('ApplyRegionDamage',10000.,prop('AttemptId'));yield 1
    check('Cinematic death never shows title',not prop('TitlePlayed') and not prop('TitleActive'))
    yield 8
    check('Old cinematic timer cannot display title after death',prop('TitlePlayCount')==0 and prop('CheckpointSaved'))

    yield from presentation.fresh_debug_saved()
    q.pos(10400,4400);yield 1;key('SpaceBar');yield .2;call('ApplyRegionDamage',10000.,prop('AttemptId'));yield 1.5
    check('Death during skip return cancels pending title',not prop('TitleActive') and not prop('TitlePlayed'))

    yield from presentation.fresh_debug_saved()
    q.pos(10400,4400);yield 1;prop('VistaCamera').destroy_actor();yield 1.5
    check('Camera loss restores body without title',not prop('TitleActive') and not prop('TitlePlayed') and q.pc.get_view_target()==q.p and not q.pc.is_move_input_ignored())
    q.L.editor_request_end_play();yield 1;q.L.editor_request_begin_play();yield 3;q.setup()
    check('New session resets title state',not prop('TitlePlayed') and not prop('TitleActive') and prop('TitlePlayCount')==0)

q.run=run
if __name__=='__main__':
    # Do not let a previous run's final report masquerade as this run's result.
    for name in ['puzzle-result.json','puzzle-progress.json']:
        (q.OUT/name).unlink(missing_ok=True)
    q.start()
