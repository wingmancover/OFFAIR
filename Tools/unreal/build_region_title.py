"""Import A wordmark, preserve fallback font, and serialize HUD references; no map edits."""
import sys
from pathlib import Path
import unreal as u
sys.path.insert(0,str(Path(__file__).parent))
from graph_builder import generated_class,compile_bp

def build_texture():
    source=Path(__file__).resolve().parents[1]/'art/offair-title-a.png'
    task=u.AssetImportTask()
    for key,value in dict(filename=str(source),destination_path='/Game/OFFAIR/Region/UI',
                          destination_name='T_OFFAIRTitleA',automated=True,save=False,replace_existing=True).items():
        task.set_editor_property(key,value)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=u.load_asset('/Game/OFFAIR/Region/UI/T_OFFAIRTitleA')
    assert texture
    for key,value in dict(compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,
                          lod_group=u.TextureGroup.TEXTUREGROUP_UI,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
                          never_stream=True,srgb=True,max_texture_size=0,filter=u.TextureFilter.TF_BILINEAR,
                          address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP).items():
        texture.set_editor_property(key,value)
    assert u.get_editor_subsystem(u.EditorAssetSubsystem).save_loaded_asset(texture,False)
    return texture


def build():
    assets=u.get_editor_subsystem(u.EditorAssetSubsystem)
    path='/Game/OFFAIR/Region/UI/F_RegionTitle'
    font=u.load_asset(path) if assets.does_asset_exist(path) else assets.duplicate_asset('/Engine/EngineFonts/Roboto',path)
    assert font and font.get_editor_property('font_cache_type')==u.FontCacheType.RUNTIME
    font.set_editor_property('legacy_font_name','Bold')
    font.set_editor_property('legacy_font_size',128)
    assert assets.save_loaded_asset(font,False)
    hud=u.load_asset('/Game/OFFAIR/Region/BP_RegionHUD')
    u.get_default_object(generated_class(hud)).set_editor_property('TitleFont',font)
    u.get_default_object(generated_class(hud)).set_editor_property('TitleWordmark',build_texture())
    compile_bp(hud)
    assert assets.save_loaded_asset(hud,False)
    u.log('OFFAIR_TITLE_AUTHORED')

if __name__=='__main__':build()
