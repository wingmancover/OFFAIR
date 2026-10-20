"""Deterministic greybox authoring. All authored objects live in OFFAIR's map."""
import json
import unreal as u

MAP_PATH = '/Game/OFFAIR/Levels/Lvl_Prototype'


def retire_camera_terminal():
    """Hide the three legacy authored terminal actors without breaking old refs."""
    labels = {'OF_Terminal', 'OF_TerminalScreen', 'OF_TerminalLabel'}
    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        if actor.get_actor_label() in labels:
            actor.set_actor_hidden_in_game(True)
            actor.set_actor_enable_collision(False)


def update_narrative_layout():
    """Migrate only the authored note/gate/cache objects; preserve the rest of the map."""
    subsystem = u.get_editor_subsystem(u.EditorActorSubsystem)
    by_label = {a.get_actor_label(): a for a in subsystem.get_all_level_actors()}
    for label in ['OF_StageGate', 'OF_AnchorPlinth', 'OF_AnchorLabel', 'OF_RewindLabel']:
        if label in by_label:
            subsystem.destroy_actor(by_label[label])
    note = by_label['OF_Anchor']
    note.set_actor_location(u.Vector(245, -170, 0.3), False, True)
    note.set_actor_rotation(u.Rotator(), True)
    note.set_actor_scale3d(u.Vector(0.55, 0.38, 0.002))
    note.static_mesh_component.set_material(0, u.load_asset('/Game/OFFAIR/Materials/M_Surveillance'))
    note.set_actor_enable_collision(False)
    cache = by_label.get('OF_TrapBox')
    if not cache:
        cache = subsystem.spawn_actor_from_class(u.StaticMeshActor, u.Vector(820, 0, 35))
        cache.set_actor_label('OF_TrapBox')
        cache.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
        cache.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
    cache.set_actor_scale3d(u.Vector(0.7, 0.6, 0.65))
    cache.static_mesh_component.set_material(0, u.load_asset('/Game/OFFAIR/Materials/M_Access'))
    cache.set_actor_enable_collision(False)
    spawn = by_label.get('OF_TrapSpawn')
    if not spawn:
        spawn = subsystem.spawn_actor_from_class(u.TargetPoint, u.Vector(1120, 0, 105))
        spawn.set_actor_label('OF_TrapSpawn')
        spawn.set_actor_rotation(u.Rotator(0, 180, 0), True)
    director = by_label['OF_RunDirector']
    director.set_editor_property('CoreItem', note)
    director.set_editor_property('TrapBox', cache)
    director.set_editor_property('TrapSpawn', spawn)
    if 'OF_WeaponLabel' in by_label:
        by_label['OF_WeaponLabel'].text_render.set_text('02  /  SUPPLY CACHE')
    retire_camera_terminal()
    return {'note': note.get_path_name(), 'trap_box': cache.get_path_name(), 'trap_spawn': spawn.get_path_name()}


def build_level(classes, output_dir):
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    assets = u.get_editor_subsystem(u.EditorAssetSubsystem)
    if assets.does_asset_exist(MAP_PATH):
        assert levels.load_level(MAP_PATH)
        for actor in actors.get_all_level_actors():
            if actor.get_actor_label().startswith('OF_'):
                actors.destroy_actor(actor)
    else:
        assert levels.new_level(MAP_PATH, False)
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    settings = u.GameplayStatics.get_all_actors_of_class(world, u.WorldSettings)[0]
    settings.set_editor_property('default_game_mode', classes['mode'])
    settings.set_editor_property('force_no_precomputed_lighting', True)
    nav_config = u.new_object(u.NavigationSystemConfig, outer=settings)
    settings.set_editor_property('navigation_system_config', nav_config)
    cube = u.load_asset('/Engine/BasicShapes/Cube')
    sphere = u.load_asset('/Engine/BasicShapes/Sphere')
    grid = u.load_asset('/Game/LevelPrototyping/Materials/MI_PrototypeGrid_Gray')
    material_edit = u.MaterialEditingLibrary
    tools = u.AssetToolsHelpers.get_asset_tools()

    def material(name, rgb, glow=0.0):
        path = '/Game/OFFAIR/Materials/' + name
        if assets.does_asset_exist(path):
            return u.load_asset(path)
        mat = tools.create_asset(name, '/Game/OFFAIR/Materials', u.Material, u.MaterialFactoryNew())
        color = material_edit.create_material_expression(mat, u.MaterialExpressionConstant3Vector, -300, 0)
        color.set_editor_property('constant', u.LinearColor(*rgb, 1))
        material_edit.connect_material_property(color, '', u.MaterialProperty.MP_BASE_COLOR)
        roughness = material_edit.create_material_expression(mat, u.MaterialExpressionConstant, -300, 160)
        roughness.set_editor_property('r', 0.72)
        material_edit.connect_material_property(roughness, '', u.MaterialProperty.MP_ROUGHNESS)
        if glow:
            emissive = material_edit.create_material_expression(mat, u.MaterialExpressionConstant3Vector, -300, 300)
            emissive.set_editor_property('constant', u.LinearColor(*(x * glow for x in rgb), 1))
            material_edit.connect_material_property(emissive, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
        material_edit.recompile_material(mat)
        assets.save_loaded_asset(mat, False)
        return mat

    materials = {
        'wall': material('M_Wall', (0.055, 0.09, 0.13)),
        'dark': material('M_Equipment', (0.025, 0.035, 0.045)),
        'cyan': material('M_Anchor', (0.04, 0.7, 0.9), 1.6),
        'gold': material('M_Access', (1.0, 0.48, 0.06), 1.3),
        'red': material('M_Surveillance', (0.8, 0.035, 0.04), 0.4),
        'green': material('M_Exit', (0.05, 0.65, 0.28), 1.0),
    }

    def spawn(cls, name, pos, yaw=0.0, pitch=0.0):
        actor = actors.spawn_actor_from_class(cls, u.Vector(*pos), u.Rotator(pitch=pitch, yaw=yaw, roll=0.0))
        if not actor:
            raise RuntimeError('Failed to place ' + name)
        actor.set_actor_label('OF_' + name)
        return actor

    def box(name, pos, size, mat='wall', movable=False, collision=True, mesh=None):
        actor = spawn(u.StaticMeshActor, name, pos)
        comp = actor.static_mesh_component
        comp.set_mobility(u.ComponentMobility.MOVABLE if movable else u.ComponentMobility.STATIC)
        comp.set_static_mesh(mesh or cube)
        comp.set_material(0, materials[mat] if isinstance(mat, str) else mat)
        actor.set_actor_scale3d(u.Vector(*(x / 100 for x in size)))
        actor.set_actor_enable_collision(collision)
        return actor

    def sign(name, text, pos, yaw=180.0, size=27.0, color=(195, 235, 255)):
        actor = spawn(u.TextRenderActor, name, pos, yaw)
        component = actor.text_render
        component.set_text(text)
        component.set_world_size(size)
        component.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
        component.set_text_render_color(u.Color(*color, 255))
        return actor

    # Enclosed, readable sequence: anchor bay -> combat bay -> terminal alcove
    # -> narrow surveillance corridor -> green exit. Wall height prevents skips.
    box('Floor', (1650, 0, -25), (4400, 1240, 50), grid)
    box('NorthWall', (1650, 610, 250), (4400, 30, 500))
    box('SouthWall', (1650, -610, 250), (4400, 30, 500))
    box('StartWall', (-550, 0, 250), (30, 1240, 500))
    box('EndWall', (3850, 0, 250), (30, 1240, 500))
    box('BayDividerNorth', (2150, 410, 250), (35, 380, 500))
    box('BayDividerSouth', (2150, -410, 250), (35, 380, 500))
    box('CorridorNorth', (2800, 235, 250), (1300, 30, 500))
    box('CorridorSouth', (2800, -235, 250), (1300, 30, 500))
    exit_gate = box('ExitGate', (3420, 0, 220), (30, 440, 440), 'red', True)
    box('CoverLeft', (1120, -250, 95), (150, 200, 190), 'dark')
    box('CoverRight', (1250, 300, 95), (150, 180, 190), 'dark')
    box('TerminalCover', (1840, -260, 110), (350, 40, 220), 'dark')
    # Thin inlaid route stripes and landmarks make the camera view legible.
    box('AnchorStripe', (150, 0, 1), (650, 12, 2), 'cyan', collision=False)
    box('CombatStripe', (1370, 0, 1), (1450, 12, 2), 'gold', collision=False)
    box('SurveillanceFloor', (2780, 0, 2), (1120, 390, 3), 'red', collision=False)
    box('ExitFloor', (3630, 0, 3), (350, 400, 4), 'green', collision=False)

    core = box('Anchor', (245, -170, 0.3), (55, 38, 0.2), 'red', True, False)
    access = box('AccessCard', (0, 0, -500), (12, 48, 32), 'gold', True, False)
    terminal = box('Terminal', (1940, -500, 80), (75, 75, 160), 'dark', True)
    box('TerminalScreen', (1900, -500, 115), (5, 62, 60), 'cyan', collision=False)

    start = spawn(u.PlayerStart, 'PlayerStart', (-160, 0, 105))
    start.set_editor_property('tags', ['0'])
    enemy_spawn = spawn(u.TargetPoint, 'GuardSpawn', (1550, 0, 105), 180)
    gm_spawn = spawn(u.TargetPoint, 'GMSpawn', (1380, -420, 105), 180)
    pickup_cls = u.load_class(None, '/Game/Variant_Shooter/Blueprints/Pickups/BP_ShooterPickup.BP_ShooterPickup_C')
    pickup = spawn(pickup_cls, 'PistolPickup', (820, 0, 70))
    pickup.set_editor_property('Weapon Type', u.DataTableRowHandle(
        data_table=u.load_asset('/Game/Variant_Shooter/Blueprints/Pickups/DT_WeaponList'), row_name='Pistol'))

    camera = spawn(u.CameraActor, 'Monitor', (2950, 0, 315), 180, -18)
    camera.camera_component.set_field_of_view(70.0)
    housing = box('CameraHousing', (2973, 0, 325), (45, 30, 30), 'dark', True, False)
    housing.attach_to_actor(camera, '', u.AttachmentRule.KEEP_WORLD, u.AttachmentRule.KEEP_WORLD, u.AttachmentRule.KEEP_WORLD, False)
    housing.set_owner(camera)
    housing.static_mesh_component.set_owner_no_see(True)
    lens = box('CameraLens', (2930, 0, 315), (12, 22, 22), 'cyan', True, False, sphere)
    lens.attach_to_actor(camera, '', u.AttachmentRule.KEEP_WORLD, u.AttachmentRule.KEEP_WORLD, u.AttachmentRule.KEEP_WORLD, False)
    lens.set_owner(camera)
    lens.static_mesh_component.set_owner_no_see(True)
    lens.static_mesh_component.set_cast_shadow(False)
    box('CameraSupport', (2950, 230, 350), (35, 470, 25), 'dark', collision=False)
    scan_light = spawn(u.SpotLight, 'ScanLight', (2950, 0, 310), 180, -18)
    scan_light.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    scan_light.light_component.set_intensity(8000.0)
    scan_light.light_component.set_light_color(u.LinearColor(1, 0.04, 0.03, 1))
    scan_light.light_component.set_editor_property('attenuation_radius', 1600.0)
    scan_light.light_component.set_editor_property('outer_cone_angle', 38.0)
    scan_light.attach_to_actor(camera, '', u.AttachmentRule.KEEP_WORLD, u.AttachmentRule.KEEP_WORLD, u.AttachmentRule.KEEP_WORLD, False)

    sign('Title', 'OFFAIR  /  RECURSION TEST', (-500, 0, 290), 0, 40)
    sign('WeaponLabel', '02  /  SUPPLY CACHE', (850, 0, 235), 180, 22, (255, 200, 120))
    sign('TerminalLabel', '03  /  CAMERA LINK\nACCESS CARD + E', (1900, -500, 230), 180, 20)
    sign('CorridorWarning', 'SURVEILLANCE ZONE\nTURN CAMERA AWAY', (2165, 0, 340), 180, 22, (255, 130, 120))
    sign('ExitLabel', '04  /  EXIT', (3790, 0, 270), 180, 40, (140, 255, 190))

    sun = spawn(u.DirectionalLight, 'Sun', (1400, 0, 900), -35, -55)
    sun.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    sun.light_component.set_intensity(3.0)
    sky = spawn(u.SkyLight, 'Sky', (1400, 0, 900))
    sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    sky.light_component.set_editor_property('real_time_capture', True)
    spawn(u.SkyAtmosphere, 'Atmosphere', (0, 0, 0))
    for index, (pos, color) in enumerate([
        ((100, -100, 330), (0.15, 0.7, 1.0)),
        ((1400, 0, 370), (1.0, 0.65, 0.3)),
        ((1930, -470, 310), (0.1, 0.7, 1.0)),
        ((3620, 0, 320), (0.12, 1.0, 0.4)),
    ]):
        light = spawn(u.PointLight, f'Light{index}', pos)
        light.light_component.set_mobility(u.ComponentMobility.MOVABLE)
        light.light_component.set_intensity(5000)
        light.light_component.set_light_color(u.LinearColor(*color, 1))
        light.light_component.set_editor_property('attenuation_radius', 1000.0)

    nav = spawn(u.NavMeshBoundsVolume, 'Navigation', (1650, 0, 200))
    origin, extent = nav.get_actor_bounds(False)
    if min(extent.x, extent.y, extent.z) <= 0:
        raise RuntimeError('Navigation volume has no brush bounds')
    nav.set_actor_scale3d(u.Vector(2200 / extent.x, 600 / extent.y, 400 / extent.z))
    nav_system = u.NavigationSystemV1.get_navigation_system(world)
    if nav_system:
        nav_system.on_navigation_bounds_updated(nav)
        # RebuildNavigation requires an existing NavDataSet. The editor's path
        # build command also creates the initial Recast actor for a new map.
        u.SystemLibrary.execute_console_command(world, 'BUILDPATHS')
    for recast in u.GameplayStatics.get_all_actors_of_class(world, u.RecastNavMesh):
        recast.set_actor_label('OF_RecastNavMesh')
        recast.set_editor_property('runtime_generation', u.RuntimeGenerationType.DYNAMIC)

    director = spawn(classes['director'], 'RunDirector', (-300, -450, 100))
    refs = {'CoreItem': core, 'AccessItem': access, 'Terminal': terminal,
            'ExitGate': exit_gate, 'WeaponPickup': pickup, 'Monitor': camera,
            'EnemySpawn': enemy_spawn, 'GMSpawn': gm_spawn}
    for name, actor in refs.items():
        director.set_editor_property(name, actor)
    update_narrative_layout()
    assert levels.save_current_level()
    report = {'map': MAP_PATH, 'director': director.get_path_name(),
              'references': {name: actor.get_path_name() for name, actor in refs.items()},
              'actor_count': len(actors.get_all_level_actors()),
              'navigation_system': nav_system.get_path_name() if nav_system else None,
              'nav_data_count': len(u.GameplayStatics.get_all_actors_of_class(world, u.RecastNavMesh)),
              'navigation_extent': str(nav.get_actor_bounds(False)[1])}
    (output_dir / 'level-result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
