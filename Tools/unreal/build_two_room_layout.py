"""Step 1: author the approved v0.3 space, without replacing the playable prototype.

Run in UnrealEditor-Cmd with -run=pythonscript -script=<this file>.
Only the dedicated map and Layout material folder are written. The preview uses
the existing FirstPerson GameMode/character; POIs are tagged static placeholders.
Re-running replaces only actors tagged OFFAIR_LAYOUT_V03 in this dedicated map.
This is the step-1 base generator. After a deliberate full rebuild, run
build_region_loop.py and validate_region_navigation.py to reapply step 2.
For ordinary step-2 changes use the incremental author; do not rebuild this layout.
"""
import json
import math
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/TwoRoomLayout'
MAP = '/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout'
MAT_DIR = '/Game/OFFAIR/Materials/Layout'
TAG = 'OFFAIR_LAYOUT_V03'
LEVELS = u.get_editor_subsystem(u.LevelEditorSubsystem)
ACTORS = u.get_editor_subsystem(u.EditorActorSubsystem)
ASSETS = u.get_editor_subsystem(u.EditorAssetSubsystem)
MATS = {}
POIS = {}
CREATED = []


def material(name, color, roughness=0.65, metallic=0.0, glow=0.0, unlit=False, two_sided=False):
    path = MAT_DIR + '/M_Lay_' + name
    if ASSETS.does_asset_exist(path):
        return u.load_asset(path)
    mat = u.AssetToolsHelpers.get_asset_tools().create_asset('M_Lay_' + name, MAT_DIR, u.Material, u.MaterialFactoryNew())
    lib = u.MaterialEditingLibrary
    if name in ['amber', 'cyan']:
        # Reused static pistol mesh requires this flag to be saved for later cook.
        mat.set_editor_property('used_with_nanite', True)
    mat.set_editor_property('two_sided', two_sided)
    if unlit:
        mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    rgb = lib.create_material_expression(mat, u.MaterialExpressionConstant3Vector, -300, 0)
    rgb.set_editor_property('constant', u.LinearColor(*color, 1))
    lib.connect_material_property(rgb, '', u.MaterialProperty.MP_BASE_COLOR)
    for index, (prop, value) in enumerate([(u.MaterialProperty.MP_ROUGHNESS, roughness), (u.MaterialProperty.MP_METALLIC, metallic)]):
        node = lib.create_material_expression(mat, u.MaterialExpressionConstant, -300, 140 + index * 120)
        node.set_editor_property('r', value)
        lib.connect_material_property(node, '', prop)
    if glow or unlit:
        node = lib.create_material_expression(mat, u.MaterialExpressionConstant3Vector, -300, 400)
        node.set_editor_property('constant', u.LinearColor(*(c * (glow or 1) for c in color), 1))
        lib.connect_material_property(node, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.recompile_material(mat)
    assert ASSETS.save_loaded_asset(mat, False)
    return mat


def spawn(cls, name, pos, rot=(0, 0, 0), folder='Architecture'):
    a = ACTORS.spawn_actor_from_class(cls, u.Vector(*pos), u.Rotator(pitch=rot[0], yaw=rot[1], roll=rot[2]))
    if not a:
        raise RuntimeError('Could not spawn ' + name)
    a.set_actor_label('OA_' + name)
    a.set_editor_property('tags', [TAG])
    a.set_folder_path('OFFAIR_Layout/' + folder)
    CREATED.append(a)
    return a


def box(name, pos, size, mat='ivory', collision=True, rot=(0, 0, 0), folder='Architecture', mesh=None):
    a = spawn(u.StaticMeshActor, name, pos, rot, folder)
    c = a.static_mesh_component
    c.set_static_mesh(mesh or u.load_asset('/Engine/BasicShapes/Cube'))
    c.set_material(0, MATS[mat])
    a.set_actor_scale3d(u.Vector(*(v / 100 for v in size)))
    a.set_actor_enable_collision(collision)
    if not collision:
        c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    if folder in ['Dome', 'Vista']:
        c.set_cast_shadow(False)
    return a


def beam(name, p1, p2, width, mat, folder='Architecture', collision=False):
    a, b = u.Vector(*p1), u.Vector(*p2)
    delta = b - a
    rot = u.MathLibrary.find_look_at_rotation(a, b)
    mid = (a + b) * 0.5
    return box(name, (mid.x, mid.y, mid.z), (delta.length(), width, width), mat, collision,
               (rot.pitch, rot.yaw, rot.roll), folder)


def text(name, value, pos, yaw=180, size=32, color=(224, 239, 245), folder='Signage'):
    a = spawn(u.TextRenderActor, name, pos, (0, yaw, 0), folder)
    c = a.text_render
    c.set_text(value)
    c.set_world_size(size)
    c.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
    c.set_vertical_alignment(u.VerticalTextAligment.EVRTA_TEXT_CENTER)
    c.set_text_render_color(u.Color(*color, 255))
    a.set_actor_enable_collision(False)
    return a


def poi(key, pos, kind, note):
    a = spawn(u.TargetPoint, 'POI_' + key, pos, folder='POI_References')
    a.set_editor_property('tags', [TAG, 'OFFAIR_POI', key, kind])
    POIS[key] = {'actor': a.get_path_name(), 'position_cm': list(pos), 'kind': kind, 'step1': note}
    return a


def line_floor(name, points, color='cyan', width=8):
    for i in range(len(points) - 1):
        beam(name + '_' + str(i), (*points[i], 0.9), (*points[i + 1], 0.9), width, color, 'Wayfinding')


def wall(name, p1, p2, accent='cyan'):
    x1, y1 = p1
    x2, y2 = p2
    length = math.hypot(x2 - x1, y2 - y1)
    yaw = math.degrees(math.atan2(y2 - y1, x2 - x1))
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    box(name, (cx, cy, 250), (length, 24, 500), 'ivory', rot=(0, yaw, 0))
    for z, thick, material_name in [(24, 48, 'metal'), (458, 84, 'metal'), (410, 7, accent)]:
        box(name + '_Band' + str(z), (cx, cy, z), (length, 28, thick), material_name,
            collision=False, rot=(0, yaw, 0))
    segments = max(1, round(length / 400))
    for i in range(segments + 1):
        t = i / segments
        box(name + '_Seam' + str(i), (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, 235),
            (3, 28, 350), 'seam', collision=False, rot=(0, yaw, 0))


def floor(name, x0, y0, x1, y1, grid=True):
    box(name, ((x0 + x1) / 2, (y0 + y1) / 2, -20), (x1 - x0, y1 - y0, 40), 'floor')
    if grid:
        for x in range(int(x0 + 400), int(x1), 400):
            box(name + '_X' + str(x), (x, (y0 + y1) / 2, 0.6), (2, y1 - y0, 0.3), 'seam', False, folder='FloorDetails')
        for y in range(int(y0 + 400), int(y1), 400):
            box(name + '_Y' + str(y), ((x0 + x1) / 2, y, 0.6), (x1 - x0, 2, 0.3), 'seam', False, folder='FloorDetails')


def gate_frame(name, x, y, width=600, yaw=0, color='cyan'):
    # Empty opening for this layout walk. A future gate will use the POI ref.
    for sign in [-1, 1]:
        dx, dy = -math.sin(math.radians(yaw)) * sign * width / 2, math.cos(math.radians(yaw)) * sign * width / 2
        box(name + '_Jamb' + str(sign), (x + dx, y + dy, 250), (65, 42, 500), 'metal', rot=(0, yaw, 0))
        box(name + '_LED' + str(sign), (x + dx - 34 * math.cos(math.radians(yaw)), y + dy - 34 * math.sin(math.radians(yaw)), 240),
            (4, 10, 390), color, False, (0, yaw, 0))
    box(name + '_Lintel', (x, y, 465), (70, width + 42, 70), 'metal', rot=(0, yaw, 0))


def point_light(name, pos, color, intensity=1800, radius=1800):
    a = spawn(u.PointLight, name, pos, folder='Lighting')
    c = a.light_component
    c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_intensity(intensity)
    c.set_light_color(u.LinearColor(*color, 1))
    c.set_editor_property('attenuation_radius', radius)
    c.set_cast_shadows(False)
    return a


def terminal(name, x, y, color='cyan', yaw=180, label=''):
    box(name + '_Base', (x, y, 12), (100, 95, 24), 'metal', folder='POI_Props')
    box(name + '_Stem', (x, y, 72), (50, 65, 120), 'metal', folder='POI_Props')
    box(name + '_Case', (x, y, 138), (30, 100, 75), 'metal', rot=(0, yaw, 0), folder='POI_Props')
    # Screen faces local +X, matching TextRender normal.
    dx, dy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    box(name + '_Display', (x + dx * 16, y + dy * 16, 138), (1, 84, 55), color, False, (0, yaw, 0), 'POI_Props')
    if label:
        text(name + '_Caption', label, (x + dx * 18, y + dy * 18, 140), yaw, 13, (240, 250, 255))


def camera(key, x, y, yaw):
    poi(key, (x, y, 320), 'Camera', 'Visible device only; hacking is step 3/4')
    a = spawn(u.CameraActor, key + '_Camera', (x, y, 320), (-12, yaw, 0), 'POI_Props')
    a.camera_component.set_field_of_view(70)
    box(key + '_Post', (x, y, 150), (18, 18, 300), 'metal', folder='POI_Props')
    box(key + '_Base', (x, y, 8), (75, 75, 16), 'metal', folder='POI_Props')
    box(key + '_Housing', (x, y, 320), (65, 35, 32), 'ivory', rot=(0, yaw, 0), folder='POI_Props')
    dx, dy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    box(key + '_Lens', (x + dx * 34, y + dy * 34, 320), (4, 23, 23), 'cyan', False, (0, yaw, 0), 'POI_Props')
    return a


def gun(key, x, y, color, caption):
    poi(key, (x, y, 116), 'WeaponChoice', 'Static display; weapon interaction is step 3')
    box(key + '_Plinth', (x, y, 48), (140, 150, 96), 'metal', folder='POI_Props')
    box(key + '_Top', (x, y, 98), (145, 155, 6), color, False, folder='POI_Props')
    weapon = box(key + '_Weapon', (x, y, 125), (180, 180, 180), color, False,
                 (0, 90, -12), 'POI_Props', u.load_asset('/Game/Weapons/Pistol/Meshes/SM_Pistol'))
    text(key + '_Sign', caption, (x - 73, y, 55), 180, 16)
    return weapon


def dome():
    center = (48000, 24000, -800)
    radius, height = 78000, 26000
    box('Dome_Shell', center, (radius * 2, radius * 2, height * 2), 'dome', False,
        folder='Dome', mesh=u.load_asset('/Engine/BasicShapes/Sphere'))
    def p(theta, angle):
        # Inset ribs below the coarse sphere shell to prevent partial occlusion.
        return (center[0] + radius * 0.98 * math.sin(theta) * math.cos(angle),
                center[1] + radius * 0.98 * math.sin(theta) * math.sin(angle),
                center[2] + height * 0.98 * math.cos(theta) - 100)
    for meridian in range(16):
        angle = meridian * math.tau / 16
        for j in range(20):
            beam('Dome_Rib_%02d_%02d' % (meridian, j), p(j * math.pi / 40, angle),
                 p((j + 1) * math.pi / 40, angle), 95, 'dome_rib', 'Dome')
    for ring, theta in enumerate([0.28, 0.52, 0.78, 1.04, 1.3, 1.53]):
        for j in range(64):
            beam('Dome_Ring_%02d_%02d' % (ring, j), p(theta, j * math.tau / 64),
                 p(theta, (j + 1) * math.tau / 64), 55, 'dome_rib', 'Dome')
    # 1080m square footprint, intentionally just scenery beyond this iteration.
    box('Arena_Datum', (48000, 24000, -850), (108000, 108000, 100), 'vista_floor', False, folder='Vista')
    # Sparse massing gives the platform a readable lower elevation and scale.
    for i, (x, y, sx, sy, z) in enumerate([(15000,4200,1800,2400,600),(19000,8500,2600,3600,1100),
            (24500,3800,2500,1800,1800),(15500,-3200,1600,3600,900),(28500,14000,3300,2600,1600),
            (36000,6000,3200,2300,2400),(27000,-5500,2200,2800,1200),(43000,19000,3500,3000,2600)]):
        box('Vista_Block' + str(i), (x, y, -800 + z / 2), (sx, sy, z), 'vista', False, folder='Vista')
        box('Vista_Band' + str(i), (x, y, -800 + z - 80), (sx + 10, sy + 10, 60), 'cyan_dim', False, folder='Vista')


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    if ASSETS.does_asset_exist(MAP):
        assert LEVELS.load_level(MAP)
        for a in ACTORS.get_all_level_actors():
            if a.actor_has_tag(TAG):
                ACTORS.destroy_actor(a)
    else:
        assert LEVELS.new_level(MAP, False)
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    ws = u.GameplayStatics.get_all_actors_of_class(world, u.WorldSettings)[0]
    ws.set_editor_property('default_game_mode', u.load_class(None, '/Game/FirstPerson/Blueprints/BP_FirstPersonGameMode.BP_FirstPersonGameMode_C'))
    ws.set_editor_property('force_no_precomputed_lighting', True)
    ws.set_editor_property('navigation_system_config', u.new_object(u.NavigationSystemConfig, outer=ws))
    specs = {
        'ivory': ((0.62,0.67,0.69),0.65,0.12,0), 'floor': ((0.30,0.35,0.38),0.72,0.08,0),
        'metal': ((0.035,0.055,0.07),0.4,0.65,0), 'seam': ((0.13,0.17,0.20),0.7,0.15,0),
        'cyan': ((0.025,0.62,0.78),0.4,0.1,2.0), 'cyan_dim': ((0.025,0.25,0.35),0.55,0.1,0.6),
        'amber': ((0.95,0.39,0.035),0.45,0.2,0.75), 'red': ((0.7,0.025,0.04),0.75,0,0.1),
        'white': ((0.85,0.91,1.0),0.5,0,1.0), 'green': ((0.08,0.65,0.40),0.5,0,1.0),
        'vista': ((0.12,0.19,0.24),0.8,0.15,1), 'vista_floor': ((0.12,0.17,0.20),0.8,0,1),
    }
    for key, (rgb, rough, metal, glow) in specs.items():
        MATS[key] = material(key, rgb, rough, metal, glow)
    MATS['dome'] = material('dome', (0.20,0.32,0.48), glow=2.5, unlit=True, two_sided=True)
    MATS['dome_rib'] = material('dome_rib', (0.30,0.50,0.70), glow=3.0, unlit=True)
    floor('TutorialFloor',0,0,4800,3600)
    for args in [('TutorialWest',(0,0),(0,3600)),('TutorialSouth',(0,0),(4800,0)),
                 ('TutorialNorth',(0,3600),(4800,3600)),('TutorialEastSouth',(4800,0),(4800,1500)),
                 ('TutorialEastNorth',(4800,2100),(4800,3600))]:
        wall(*args)
    floor('PuzzleFloor',5200,2600,8800,6200)
    for args in [('PuzzleWest',(5200,2600),(5200,6200)),('PuzzleNorth',(5200,6200),(8800,6200)),
                 ('PuzzleSouthWest',(5200,2600),(5700,2600)),('PuzzleSouthEast',(6300,2600),(8800,2600)),
                 ('PuzzleEastSouth',(8800,2600),(8800,4100)),('PuzzleEastNorth',(8800,4700),(8800,6200))]:
        wall(*args, accent='amber')
    floor('CorridorEast',4800,1500,6300,2100,False)
    floor('CorridorNorth',5700,2100,6300,2600,False)
    for args in [('CorridorSouth',(4800,1500),(6300,1500)),('CorridorOuter',(6300,1500),(6300,2600)),
                 ('CorridorInnerEast',(4800,2100),(5700,2100)),('CorridorInnerNorth',(5700,2100),(5700,2600))]:
        wall(*args)
    gate_frame('D1',4800,1800)
    gate_frame('PuzzleEntry',6000,2600,yaw=90,color='amber')
    gate_frame('D2',8800,4400,color='green')
    floor('BHall',8800,4100,9600,4700,False)
    wall('BHallSouth',(8800,4100),(9600,4100),'green')
    wall('BHallNorth',(8800,4700),(9600,4700),'green')
    floor('VistaPlatform',9600,3800,11000,5000)
    box('VistaPlatformFascia',(10300,4400,-400),(1400,1200,760),'metal')
    rail_posts=set()
    for i,(a,b) in enumerate([((9600,3800),(11000,3800)),((11000,3800),(11000,5000)),
                             ((11000,5000),(9600,5000)),((9600,3800),(9600,4100)),((9600,4700),(9600,5000))]):
        # Low structural parapet prevents leaving the bounded layout test.
        beam('PlatformRail'+str(i),(*a,110),(*b,110),12,'metal',collision=True)
        beam('PlatformRailLow'+str(i),(*a,45),(*b,45),12,'metal',collision=True)
        length=math.dist(a,b)
        for j in range(max(1,round(length/200))+1):
            t=j/max(1,round(length/200))
            post=(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,55)
            if post not in rail_posts:
                box('RailPost_%d_%d'%(i,j),post,(10,10,110),'metal')
                rail_posts.add(post)
        # The thin no-draw collision rail is taller than jump height.
        barrier=beam('PlatformSafety'+str(i),(*a,170),(*b,170),1,'metal',collision=True)
        barrier.set_actor_scale3d(u.Vector(length/100,0.15,3.4))
        barrier.set_actor_hidden_in_game(True)

    start=spawn(u.PlayerStart,'StartA',(400,1800,100),folder='POI_References')
    poi('A',(400,1800,100),'Checkpoint','Starting reference; no checkpoint logic in step 1')
    poi('N',(800,1800,1),'MemoryNote','Static red letter')
    box('RedNote',(800,1800,1),(55,38,0.7),'red',False,(0,12,0),'POI_Props')
    for i in range(4):
        box('NoteWriting'+str(i),(795+i*6,1800,1.6),(1.5,20-i*2,0.15),'ivory',False,(0,12,0),'POI_Props')
    gun('G1',1500,2400,'amber','01 / RECOMMENDED')
    gun('G2',1500,1200,'cyan','02 / ALTERNATIVE')
    for i,(x,y) in enumerate([(2500,2400),(2900,1200),(3400,2000)]):
        box('Cover'+str(i),(x,y,110),(260,260,220),'metal')
        box('CoverCap'+str(i),(x,y,222),(268,268,12),'ivory')
        box('CoverStripe'+str(i),(x-132,y,100),(3,230,18),'cyan_dim',False)
    for key,x,y in [('E1',3600,2800),('E2',3600,800),('E3',2400,3400),('E4',3400,3400),('E5',2400,200),('E6',3400,200)]:
        poi(key,(x,y,100),'EnemySpawn','Marker only; no enemies in layout preview')
        if key not in ['E1','E2']:
            box(key+'_LocalScreen',(x,y+(-180 if y>1800 else 180),130),(300,40,260),'metal')
    camera('C1',4300,2700,225)
    poi('L1',(4000,1800,0),'CameraLearningPosition','Approach position')
    poi('D1',(4800,1800,0),'CombatGate','Open for layout walk')
    box('VaultObstacle',(400,800,45),(100,400,90),'ivory')
    box('VaultTop',(400,800,91),(100,400,3),'cyan',False)
    poi('O',(400,800,90),'Vault','Geometry only; preview character uses ordinary jump')
    line_floor('RouteA',[(400,1800),(740,1800)],'cyan_dim',6)
    line_floor('RouteD1',[(3900,1800),(4800,1800),(6000,1800),(6000,2600)],'cyan',8)
    line_floor('CombatBoundary',[(2100,500),(2100,3100)],'amber',4)
    # Large, legible environmental signs use the existing engine distance-field font.
    box('TitlePlate',(26,1800,305),(15,1400,210),'metal',False)
    text('Title','OFF AIR',(36,1800,330),0,105)
    text('TitleSub','01 / INDUCTION',(38,1800,248),0,29,(66,200,226))
    text('D1Sign','02  /  SIGNAL LAB',(4750,1800,464),180,27)
    text('CorridorTurn','SIGNAL LAB  >',(6000,1530,270),90,30,(66,200,226))
    # Room two: puzzle cluster remains close enough for 15m hacking.
    poi('S',(6200,3800,0),'PlayerObservation','Camera distance approx 13.1m')
    poi('P',(6600,3800,160),'PuzzlePanel','Static 3x3 shooting board')
    box('PuzzlePanelFrame',(6600,3800,160),(40,300,300),'metal',folder='POI_Props')
    box('PuzzlePanelFoot',(6600,3800,10),(120,350,20),'metal',folder='POI_Props')
    for row in range(3):
        for col in range(3):
            box('PuzzleTile_%d_%d'%(row,col),(6577,3800+(col-1)*82,160+(1-row)*82),(8,75,75),'ivory',folder='POI_Props')
    text('PanelHeader','PATTERN INPUT',(6570,3800,337),180,22)
    poi('F',(6600,4600,190),'FalsePattern','Static example; narrative/answer logic pending')
    box('FalsePatternFrame',(6600,4600,190),(30,220,220),'metal',folder='POI_Props')
    for i in range(9):
        box('FalsePatternCell'+str(i),(6583,4600+(i%3-1)*57,190+(1-i//3)*57),(4,48,48),
            'amber' if i in [0,1,2,4,7] else 'seam',False,folder='POI_Props')
    text('FalsePatternLabel','BROADCAST REFERENCE',(6578,4600,322),180,17,(245,190,86))
    camera('C2',7400,4300,80)
    poi('T',(7600,5600,360),'TruePattern','Composition target placeholder; camera-only highlight is step 4')
    box('TruePatternBack',(7600,5620,360),(380,20,180),'metal',False,folder='POI_Props')
    for i,(dx,dz) in enumerate([(-90,45),(-90,0),(-90,-45),(-30,-45),(30,-45)]):
        box('TrueFragment'+str(i),(7600+dx,5605,360+dz),(45,5,36),'cyan_dim',False,folder='POI_Props')
    poi('R',(6400,3400,140),'PuzzleControls','Clear/submit station placeholder')
    terminal('PuzzleControls',6400,3400,label='CLEAR / SUBMIT')
    poi('D2',(8800,4400,0),'PuzzleGate','Open for layout walk')
    poi('B',(9200,4400,0),'Checkpoint','Memory terminal placeholder; save logic is step 2')
    terminal('MemoryB',9200,4650,'green',270,'MEMORY / B')
    poi('V',(10400,4400,170),'Vista','Walkable overlook; cinematic is step 5')
    poi('K1',(10400,4400,170),'CinematicStart','Reference only')
    poi('K2',(9700,4400,1400),'CinematicEnd','Reference only')
    line_floor('PuzzleRoute',[(6000,2600),(6000,3300),(6200,3800)],'amber',6)
    line_floor('ExitRoute',[(7000,3100),(8300,3100),(8300,4400),(9600,4400)],'green',6)
    text('PuzzleTitle','02 / SIGNAL LAB',(7000,6165,350),270,72)
    text('PuzzleTitleSub','OBSERVE / INTERPRET / RESPOND',(7000,6160,258),270,26,(245,190,86))
    text('D2Sign','MEMORY TRANSFER',(8750,4400,464),180,28,(130,245,193))
    text('PlatformSign','03 / THE ARENA',(9660,4955,220),270,25)
    # Speaker housings establish the host's physical broadcast presence.
    for i,(x,y,yaw) in enumerate([(900,3560,270),(4200,40,90),(5600,6160,270),(8500,2640,90)]):
        box('Speaker'+str(i),(x,y,360),(90,35,120),'metal',False,(0,yaw-90,0),'SetDressing')
        for j in range(5):
            box('SpeakerSlat_%d_%d'%(i,j),(x,y+(20 if y<3000 else -20),330+j*14),(70,3,4),'seam',False,folder='SetDressing')
    dome()
    sun=spawn(u.DirectionalLight,'FacilityKey',(3000,2500,1500),(-55,-25,0),'Lighting')
    sun.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    sun.light_component.set_intensity(5.0)
    sun.light_component.set_light_color(u.LinearColor(0.82,0.91,1,1))
    sky=spawn(u.SkyLight,'FacilityFill',(3000,2500,1800),folder='Lighting')
    sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    sky.light_component.set_intensity(0.9)
    sky.light_component.set_editor_property('real_time_capture',True)
    spawn(u.SkyAtmosphere,'Atmosphere',(0,0,0),folder='Lighting')
    for i,(pos,rgb) in enumerate([((1000,1800,430),(0.5,0.8,1)),((3000,1800,450),(1,0.82,0.6)),
            ((4500,1800,430),(0.4,0.75,1)),((6000,1800,400),(0.5,0.85,1)),
            ((6500,3600,450),(1,0.82,0.63)),((7600,5000,450),(0.55,0.8,1)),
            ((9200,4400,400),(0.5,1,0.78))]):
        point_light('Fill'+str(i),pos,rgb,2400,2100)
    pp=spawn(u.PostProcessVolume,'Exposure',(0,0,0),folder='Lighting')
    pp.set_editor_property('unbound',True)
    settings=pp.get_editor_property('settings')
    for key,value in {'auto_exposure_min_brightness':3.0,'auto_exposure_max_brightness':3.0,
                      'auto_exposure_bias':0.0,'bloom_intensity':0.12,'motion_blur_amount':0.0}.items():
        settings.set_editor_property('override_'+key,True)
        settings.set_editor_property(key,value)
    pp.set_editor_property('settings',settings)
    nav=spawn(u.NavMeshBoundsVolume,'Navigation',(5500,3100,200),folder='Navigation')
    _,extent=nav.get_actor_bounds(False)
    assert min(extent.x,extent.y,extent.z)>0
    nav.set_actor_scale3d(u.Vector(5650/extent.x,3250/extent.y,500/extent.z))
    system=u.NavigationSystemV1.get_navigation_system(world)
    if system:
        system.on_navigation_bounds_updated(nav)
    u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(u.Vector(400,1800,175),u.Rotator(pitch=0,yaw=0,roll=0))
    assert LEVELS.save_current_level()
    report={'status':'authored','map':MAP,'actor_count':len(CREATED),'pois':POIS,
            'tutorial_size_m':[48,36],'puzzle_size_m':[36,36],
            'corridor_centerline_cm':[[4800,1800,0],[6000,1800,0],[6000,2600,0]],
            'corridor_width_m':6,'corridor_ideal_seconds':20/6,
            'preview_game_mode':'BP_FirstPersonGameMode','navigation_verified':False,
            'old_map_modified':False,'gameplay_connected':False}
    (OUT/'build-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    u.log('OFFAIR_TWO_ROOM_LAYOUT_AUTHORED '+MAP)


if __name__=='__main__':
    build()
