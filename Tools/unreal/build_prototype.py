"""Author the OFFAIR prototype as native Blueprint assets and a compact map.

Run with UnrealEditor-Cmd -run=pythonscript -script=<this file>.
Only /Game/OFFAIR assets are authored. Template assets remain untouched.
"""
import json
import sys
from pathlib import Path
import unreal as u

sys.path.insert(0, str(Path(__file__).parent))
from graph_builder import Graph, LIB, EDITOR, create_bp, compile_bp, declare, member, pin, put, generated_class, class_path, save

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved' / 'PrototypeBuild'
OUT.mkdir(parents=True, exist_ok=True)
ASSETS = u.get_editor_subsystem(u.EditorAssetSubsystem)
BASE = '/Game/OFFAIR'
MAP = BASE + '/Levels/Lvl_Prototype'
SHOOTER = '/Game/Variant_Shooter/Blueprints/BP_ShooterCharacter.BP_ShooterCharacter_C'
SHOOTER_PC = '/Game/Variant_Shooter/Blueprints/BP_ShooterPlayerController.BP_ShooterPlayerController_C'
SHOOTER_GM = '/Game/Variant_Shooter/Blueprints/BP_ShooterGameMode.BP_ShooterGameMode_C'
NPC = '/Game/Variant_Shooter/Blueprints/AI/BP_ShooterNPC.BP_ShooterNPC_C'
WEAPON = '/Game/Variant_Shooter/Blueprints/Pickups/BP_ShooterWeaponBase.BP_ShooterWeaponBase_C'
ACTOR = '/Script/Engine.Actor'
PC = '/Script/Engine.PlayerController'
VECTOR = '/Script/CoreUObject.Vector'
ROTATOR = '/Script/CoreUObject.Rotator'

BP = {
    'session': create_bp(BASE + '/Core/BP_OFFAIRSession', '/Script/Engine.GameInstance'),
    'director': create_bp(BASE + '/Core/BP_RunDirector', ACTOR),
    'player': create_bp(BASE + '/Core/BP_OFFAIRPlayer', SHOOTER),
    'controller': create_bp(BASE + '/Core/BP_OFFAIRController', SHOOTER_PC),
    'mode': create_bp(BASE + '/Core/BP_OFFAIRGameMode', SHOOTER_GM),
    'hud': create_bp(BASE + '/UI/BP_PrototypeHUD', '/Script/Engine.HUD'),
}
PATH = {k: class_path(v) for k, v in BP.items()}

# Preserve function identities during regeneration. Clear all generated bodies
# before compiling any dependent Blueprint; deleting function graphs would
# rename their replacements and invalidate callers in other generated assets.
for bp in BP.values():
    for graph in LIB.list_graphs(bp):
        if graph.get_name() == 'UserConstructionScript':
            continue
        editor = EDITOR.get_graph_editor(graph)
        editor.remove_nodes([n for n in editor.list_all_nodes()
                             if n.get_class().get_name() not in ('K2Node_FunctionEntry', 'K2Node_FunctionResult')])


def vars_(key, definitions):
    for name, kind in definitions.items():
        member(BP[key], name, kind)
    compile_bp(BP[key])


vars_('session', {'CurrentStage': 'int', 'PendingStage': 'int', 'ResetTarget': 'int',
                  'ResetBusy': 'bool', 'RunNumber': 'int', 'GMEnabled': 'bool'})
vars_('director', {
    'Session': PATH['session'], 'Player': SHOOTER, 'Controller': PC,
    'CoreItem': ACTOR, 'AccessItem': ACTOR, 'Terminal': ACTOR,
    'StageGate': ACTOR, 'ExitGate': ACTOR, 'WeaponPickup': ACTOR,
    'Monitor': '/Script/Engine.CameraActor', 'KeyEnemy': NPC,
    'EnemySpawn': ACTOR, 'GMSpawn': ACTOR,
    'Stage': 'int', 'EnemyCount': 'int', 'MaxEnemies': 'int',
    'Initialized': 'bool', 'Resetting': 'bool', 'Completed': 'bool',
    'CoreCollected': 'bool', 'GuardRewarded': 'bool', 'AccessCollected': 'bool',
    'RemoteActive': 'bool', 'HackedOnce': 'bool', 'Alarm': 'bool', 'GMOpen': 'bool',
    'RemoteYaw': 'real', 'RemotePitch': 'real', 'DetectionTime': 'real',
    'StatusText': 'string', 'PromptText': 'string', 'ObjectiveText': 'string',
    'SavedView': ROTATOR, 'Enemies': 'array:' + NPC,
    'PollElapsed': 'real', 'AcceptedResets': 'int', 'FailureText': 'string',
    'ConditionEvent': 'name', 'ConditionTarget': 'name',
})
vars_('hud', {'Director': PATH['director'], 'ScreenWidth': 'real', 'ScreenHeight': 'real'})
for name in ['CoreItem', 'AccessItem', 'Terminal', 'StageGate', 'ExitGate', 'WeaponPickup', 'Monitor', 'EnemySpawn', 'GMSpawn', 'MaxEnemies', 'ConditionEvent', 'ConditionTarget']:
    LIB.set_blueprint_variable_instance_editable(BP['director'], name, True)
    LIB.set_blueprint_variable_category(BP['director'], name, 'Stage Setup')
compile_bp(BP['director'])

FUNCTIONS = {
    'session': [('SetGMEnabled', {'Enabled': 'bool'}, {})],
    'director': [
        ('InitializeRun', {}, {}),
        ('CommitRun', {}, {}),
        ('RequestReset', {'Target': 'int'}, {}),
        ('AcceptDeath', {}, {}), ('KillPlayer', {}, {}), ('Restart', {}, {}),
        ('GMStage', {'Delta': 'int'}, {}), ('GMAdd', {}, {}), ('GMRemove', {}, {}),
        ('AddEnemy', {'KeyGuard': 'bool'}, {}), ('PollEnemies', {}, {}),
        ('Interact', {}, {}), ('CanInteract', {'Target': ACTOR}, {'Result': 'bool'}),
        ('MarkCondition', {'EventId': 'name', 'TargetId': 'name'}, {}),
        ('EnterRemote', {'BypassAccess': 'bool'}, {}), ('ExitRemote', {}, {}),
        ('RefreshControls', {}, {}), ('ToggleGM', {}, {}),
        ('TickInput', {'Delta': 'real'}, {}), ('TickRemote', {'Delta': 'real'}, {}),
        ('PanRemote', {'DeltaX': 'real', 'DeltaY': 'real'}, {}),
        ('TickSurveillance', {'Delta': 'real'}, {}), ('UpdateFeedback', {}, {}),
        ('UpdateExit', {}, {}), ('CheckFinish', {}, {}), ('GMAction', {'Action': 'int'}, {}),
    ],
    'hud': [('DrawPrototype', {}, {}), ('DrawGM', {}, {}),
            ('Label', {'Text': 'string', 'X': 'real', 'Y': 'real', 'Size': 'real'}, {}),
            ('GMButton', {'Label': 'string', 'Y': 'real', 'HitName': 'name'}, {})],
}
for key, definitions in FUNCTIONS.items():
    for name, inputs, outputs in definitions:
        declare(BP[key], name, inputs, outputs)
    compile_bp(BP[key])

# This authoring script owns only its generated event graphs.
for key in BP:
    graph = LIB.find_event_graph(BP[key])
    if graph:
        editor = EDITOR.get_graph_editor(graph)
        editor.remove_nodes(editor.list_all_nodes())


def g_(name, key='director'):
    return Graph(BP[key], name)


def local(g, function, **args):
    return g.call(function, **args)


def session(g, name):
    return g.get(name, g.get('Session'), PATH['session'])


def set_session(g, name, value):
    return g.set(name, value, g.get('Session'), PATH['session'])


def ready(g, allow_complete=False):
    cond = g.and_(g.get('Initialized'), g.not_(g.get('Resetting')))
    if not allow_complete:
        cond = g.and_(cond, g.not_(g.get('Completed')))
    g.guard(cond)


def alive(g, actor):
    g.guard(g.valid(actor))
    return g.math('Greater_DoubleDouble', A=g.get('Current HP', actor, NPC), B=0.0)


def show_actor(g, actor, enabled, collision=True):
    g.engine('Actor', 'SetActorHiddenInGame', self=actor, bNewHidden=g.not_(enabled) if isinstance(enabled, u.BlueprintGraphPin) else not enabled)
    g.engine('Actor', 'SetActorEnableCollision', self=actor, bNewActorEnableCollision=enabled if collision else False)


def location(g, actor):
    return g.engine('Actor', 'K2_GetActorLocation', 'ReturnValue', self=actor)


def object_equal(g, a, b):
    return g.math('EqualEqual_ObjectObject', A=a, B=b)


def stop_weapon(g):
    weapon = g.get('Current Weapon', g.get('Player'), SHOOTER)
    g.when(g.valid(weapon), lambda b: b.call(WEAPON + ':Stop Firing', self=weapon))


def build_core():
    setting = g_('SetGMEnabled', 'session')
    setting.set('GMEnabled', setting.param('Enabled'))
    g = g_('InitializeRun')
    inst = g.engine('GameplayStatics', 'GetGameInstance', 'ReturnValue')
    cast = g.cast(inst, PATH['session'])
    g.set('Session', cast)
    pc = g.engine('GameplayStatics', 'GetPlayerController', 'ReturnValue', PlayerIndex=0)
    g.set('Controller', pc)
    g.engine('Actor', 'AddTickPrerequisiteActor', PrerequisiteActor=pc)
    pawn = g.engine('GameplayStatics', 'GetPlayerPawn', 'ReturnValue', PlayerIndex=0)
    player = g.cast(pawn, SHOOTER)
    g.set('Player', player)
    g.set('Initialized', False)
    g.set('FailureText', '')
    local(g, 'RefreshControls')
    essential = ['CoreItem', 'AccessItem', 'Terminal', 'StageGate', 'ExitGate', 'WeaponPickup', 'Monitor', 'EnemySpawn', 'GMSpawn']
    for name in essential:
        yes, no = g.branch(g.valid(g.get(name)))
        no.set('FailureText', 'Missing level reference: ' + name)
        no.log('OFFAIR_INIT_ERROR missing ' + name)
        g.tail = yes.tail
    item_pair = g.and_(g.math('EqualEqual_NameName', A=g.get('ConditionEvent'), B='ItemAcquired'),
                       g.math('EqualEqual_NameName', A=g.get('ConditionTarget'), B='Anchor'))
    guard_pair = g.and_(g.math('EqualEqual_NameName', A=g.get('ConditionEvent'), B='EnemyKilled'),
                        g.math('EqualEqual_NameName', A=g.get('ConditionTarget'), B='Guard'))
    g.guard(g.or_(item_pair, guard_pair), lambda b: b.set('FailureText', 'Invalid stage condition. Use ItemAcquired/Anchor or EnemyKilled/Guard.'))
    pending, normal = g.branch(session(g, 'ResetBusy'))
    pending.set('Stage', session(pending, 'ResetTarget'))
    normal.set('Stage', session(normal, 'CurrentStage'))
    # Both paths converge by invoking the shared finalizer event.
    pending.call('FinalizeRun')
    normal.call('FinalizeRun')

    g = g_('RequestReset')
    g.guard(g.and_(g.not_(g.get('Resetting')), g.valid(g.get('Session'))))
    target = g.param('Target')
    g.guard(g.and_(g.math('GreaterEqual_IntInt', A=target, B=0), g.math('LessEqual_IntInt', A=target, B=1)))
    g.set('Resetting', True)
    g.set('AcceptedResets', g.math('Add_IntInt', A=g.get('AcceptedResets'), B=1))
    set_session(g, 'ResetTarget', target)
    set_session(g, 'ResetBusy', True)
    g.set('GMOpen', False)
    local(g, 'ExitRemote')
    local(g, 'RefreshControls')
    g.set('StatusText', 'REWINDING / rebuilding the stage...')
    g.log('OFFAIR_RESET_ACCEPTED')
    local(g, 'ReloadWorld')

    g = g_('AcceptDeath')
    ready(g)
    yes, no = g.branch(g.math('GreaterEqual_IntInt', A=session(g, 'PendingStage'), B=0))
    yes.call('RequestReset', Target=session(yes, 'PendingStage'))
    no.call('RequestReset', Target=g.get('Stage'))

    g = g_('KillPlayer')
    ready(g)
    g.guard(g.valid(g.get('Player')))
    health = g.get('Current HP', g.get('Player'), SHOOTER)
    g.guard(g.math('Greater_DoubleDouble', A=health, B=0.0))
    g.engine('GameplayStatics', 'ApplyDamage', DamagedActor=g.get('Player'), BaseDamage=health,
             EventInstigator=g.get('Controller'), DamageTypeClass='/Script/Engine.DamageType')

    g = g_('Restart')
    ready(g, True)
    yes, no = g.branch(g.get('Completed'))
    yes.call('RequestReset', Target=0)
    no.call('KillPlayer')

    g = g_('GMStage')
    ready(g)
    g.guard(session(g, 'GMEnabled'))
    target = g.math('Add_IntInt', A=g.get('Stage'), B=g.param('Delta'))
    yes, no = g.branch(g.and_(g.math('GreaterEqual_IntInt', A=target, B=0), g.math('LessEqual_IntInt', A=target, B=1)))
    yes.call('RequestReset', Target=target)
    no.set('StatusText', 'No adjacent stage. Stage order is 0 -> 1.')

    g = g_('CommitRun')
    g.guard(g.get('Initialized'))
    set_session(g, 'CurrentStage', g.get('Stage'))
    set_session(g, 'PendingStage', -1)
    set_session(g, 'ResetBusy', False)
    set_session(g, 'RunNumber', g.math('Add_IntInt', A=session(g, 'RunNumber'), B=1))
    g.set('StatusText', 'Follow the signs. E interacts. R restarts a loop.')
    local(g, 'RefreshControls')
    g.log('OFFAIR_RUN_READY')


def build_interactions():
    g = g_('CanInteract')
    target = g.param('Target')
    g.guard(g.valid(target), lambda no: no.ret(Result=False))
    g.guard(g.valid(g.get('Player')), lambda no: no.ret(Result=False))
    distance = g.engine('Actor', 'GetDistanceTo', 'ReturnValue', self=g.get('Player'), OtherActor=target)
    g.guard(g.math('LessEqual_DoubleDouble', A=distance, B=230.0), lambda no: no.ret(Result=False))
    camera = g.engine('GameplayStatics', 'GetPlayerCameraManager', 'ReturnValue', PlayerIndex=0)
    view_pos = g.engine('PlayerCameraManager', 'GetCameraLocation', 'ReturnValue', self=camera)
    view_rot = g.engine('PlayerCameraManager', 'GetCameraRotation', 'ReturnValue', self=camera)
    forward = g.engine('KismetMathLibrary', 'GetForwardVector', 'ReturnValue', InRot=view_rot)
    direction = g.math('Subtract_VectorVector', A=location(g, target), B=view_pos)
    direction = g.engine('KismetMathLibrary', 'Normal', 'ReturnValue', A=direction, Tolerance=0.0001)
    facing = g.math('Greater_DoubleDouble', A=g.math('Dot_VectorVector', A=forward, B=direction), B=0.45)
    los = g.engine('Controller', 'LineOfSightTo', 'ReturnValue', self=g.get('Controller'), Other=target, ViewPoint=view_pos, bAlternateChecks=False)
    g.ret(Result=g.and_(facing, los))

    g = g_('MarkCondition')
    ready(g)
    g.guard(g.eq(g.get('Stage'), 0))
    event_ok = g.math('EqualEqual_NameName', A=g.param('EventId'), B=g.get('ConditionEvent'))
    target_ok = g.math('EqualEqual_NameName', A=g.param('TargetId'), B=g.get('ConditionTarget'))
    g.guard(g.and_(event_ok, target_ok))
    g.guard(g.not_(g.get('CoreCollected')))
    g.set('CoreCollected', True)
    set_session(g, 'PendingStage', 1)
    show_actor(g, g.get('CoreItem'), False, False)
    g.set('StatusText', 'CONDITION SECURED. The next death starts STAGE 1. Press R to rewind.')
    g.log('OFFAIR_CONDITION accepted; PendingStage=1')

    g = g_('Interact')
    ready(g)
    yes, body = g.branch(g.get('RemoteActive'))
    yes.call('ExitRemote')
    g.tail = body.tail
    g.guard(g.not_(g.get('GMOpen')))
    core = g.and_(g.eq(g.get('Stage'), 0), g.not_(g.get('CoreCollected')),
                  g.math('EqualEqual_NameName', A=g.get('ConditionEvent'), B='ItemAcquired'))
    core = g.and_(core, g.call('CanInteract', 'Result', Target=g.get('CoreItem')))
    g.when(core, lambda b: b.call('MarkCondition', EventId='ItemAcquired', TargetId='Anchor'))
    access = g.and_(g.eq(g.get('Stage'), 1), g.get('GuardRewarded'), g.not_(g.get('AccessCollected')))
    access = g.and_(access, g.call('CanInteract', 'Result', Target=g.get('AccessItem')))
    def collect(b):
        b.set('AccessCollected', True)
        show_actor(b, b.get('AccessItem'), False, False)
        b.set('StatusText', 'ACCESS CARD COLLECTED. Find the blue surveillance terminal.')
        b.log('OFFAIR_ACCESS_COLLECTED')
    g.when(access, collect)
    terminal = g.and_(g.eq(g.get('Stage'), 1), g.call('CanInteract', 'Result', Target=g.get('Terminal')))
    def connect(b):
        yes, no = b.branch(b.get('AccessCollected'))
        yes.call('EnterRemote', BypassAccess=False)
        no.set('StatusText', 'TERMINAL LOCKED. Defeat the guard and collect the access card.')
        b.tail = [yes.tail, no.tail]
    g.when(terminal, connect)

    g = g_('AddEnemy')
    ready(g)
    local(g, 'PollEnemies')
    within_limit = g.math('Less_IntInt', A=g.get('EnemyCount'), B=g.get('MaxEnemies'))
    g.guard(within_limit, lambda b: b.set('StatusText', 'Enemy limit reached (8).'))
    column = g.math('Percent_IntInt', A=g.get('EnemyCount'), B=3)
    row = g.math('Divide_IntInt', A=g.get('EnemyCount'), B=3)
    gm_offset = g.vec(g.math('Multiply_DoubleDouble', A=column, B=120.0), g.math('Multiply_DoubleDouble', A=row, B=140.0), 0.0)
    gm_position = g.math('Add_VectorVector', A=location(g, g.get('GMSpawn')), B=gm_offset)
    position = g.engine('KismetMathLibrary', 'SelectVector', 'ReturnValue',
        A=location(g, g.get('EnemySpawn')), B=gm_position, bPickA=g.param('KeyGuard'))
    spawned = g.spawn(NPC, g.transform(position, g.rot(0.0, 180.0)))
    good, bad = g.branch(g.valid(spawned))
    def critical_failure(b):
        b.set('Initialized', False)
        b.set('FailureText', 'Guard spawn failed. Press R to retry the stage.')
    bad.when(bad.param('KeyGuard'), critical_failure)
    bad.set('StatusText', 'Enemy could not spawn: the spawn point may be occupied.')
    g.tail = good.tail
    movement = g.get('CharacterMovement', spawned, '/Script/Engine.Character')
    g.set('MaxWalkSpeed', 220.0, movement, '/Script/Engine.CharacterMovementComponent')
    g.call('/Script/Engine.KismetArrayLibrary.Array_Add', TargetArray=g.get('Enemies'), NewItem=spawned)
    g.when(g.param('KeyGuard'), lambda b: b.set('KeyEnemy', spawned))
    g.set('EnemyCount', g.math('Add_IntInt', A=g.get('EnemyCount'), B=1))
    g.set('StatusText', 'Enemy spawned. R restores the stage baseline.')

    editor = EDITOR.get_graph_editor_by_name(BP['director'], 'PollEnemies')
    if 'Alive' not in editor.list_local_variable_names():
        editor.add_local_variable('Alive', LIB.get_array_type(LIB.get_object_reference_type(u.load_class(None, NPC))), '')
    g = g_('PollEnemies')
    ready(g)
    g.set('EnemyCount', 0)
    alive_node = g.own(g.editor.add_get_local_variable_node('Alive'))
    alive_list = pin(alive_node, 'Alive', True)
    body, enemy = g.foreach(g.get('Enemies'))
    body.guard(body.valid(enemy))
    health = body.get('Current HP', enemy, NPC)
    body.guard(body.math('Greater_DoubleDouble', A=health, B=0.0))
    body.set('EnemyCount', body.math('Add_IntInt', A=body.get('EnemyCount'), B=1))
    body.call('/Script/Engine.KismetArrayLibrary.Array_Add', TargetArray=alive_list, NewItem=enemy)
    g.set('Enemies', alive_list)
    g.guard(g.not_(g.get('GuardRewarded')))
    guard = g.get('KeyEnemy')
    g.guard(g.valid(guard))
    g.guard(g.math('LessEqual_DoubleDouble', A=g.get('Current HP', guard, NPC), B=0.0))
    g.set('GuardRewarded', True)
    g.call('MarkCondition', EventId='EnemyKilled', TargetId='Guard')
    g.guard(g.eq(g.get('Stage'), 1))
    drop = g.math('Add_VectorVector', A=location(g, guard), B=g.vec(0.0, 0.0, 65.0))
    g.engine('Actor', 'K2_SetActorLocation', self=g.get('AccessItem'), NewLocation=drop, bSweep=False, bTeleport=True)
    show_actor(g, g.get('AccessItem'), True, False)
    g.set('StatusText', 'GUARD DOWN. Look for the gold access card and press E.')
    g.log('OFFAIR_GUARD_KILLED')

    g = g_('GMAdd')
    ready(g)
    g.guard(session(g, 'GMEnabled'))
    g.call('AddEnemy', KeyGuard=False)

    # Remove the newest live enemy (extras are appended after the stage guard).
    # A reverse-index loop is unnecessary: remember each live candidate in a
    # local variable, then remove the last one after the foreach completes.
    editor = EDITOR.get_graph_editor_by_name(BP['director'], 'GMRemove')
    if 'Candidate' not in editor.list_local_variable_names():
        editor.add_local_variable('Candidate', LIB.get_object_reference_type(u.load_class(None, NPC)), 'None')
    g = g_('GMRemove')
    ready(g)
    g.guard(session(g, 'GMEnabled'))
    body, enemy = g.foreach(g.get('Enemies'))
    body.guard(body.valid(enemy))
    body.guard(body.math('Greater_DoubleDouble', A=body.get('Current HP', enemy, NPC), B=0.0))
    setter = body.own(body.editor.add_set_local_variable_node('Candidate'))
    put(pin(setter, 'Candidate'), enemy)
    body.wire_exec(setter)
    getter = g.own(g.editor.add_get_local_variable_node('Candidate'))
    candidate = pin(getter, 'Candidate', True)
    g.guard(g.valid(candidate), lambda b: b.set('StatusText', 'GM: no living enemy to remove.'))
    g.when(object_equal(g, candidate, g.get('KeyEnemy')), lambda b: b.set('KeyEnemy', None))
    controller = g.engine('Pawn', 'GetController', 'ReturnValue', self=candidate)
    g.when(g.valid(controller), lambda b: b.engine('Actor', 'K2_DestroyActor', self=controller))
    g.call('/Script/Engine.KismetArrayLibrary.Array_RemoveItem', TargetArray=g.get('Enemies'), Item=candidate)
    g.engine('Actor', 'K2_DestroyActor', self=candidate)
    g.call('PollEnemies')
    g.set('StatusText', 'GM: enemy removed without kill rewards. R restores the stage.')


def build_remote():
    g = g_('RefreshControls')
    g.guard(g.valid(g.get('Player')))
    g.guard(g.valid(g.get('Controller')))
    blocked = g.or_(g.get('RemoteActive'), g.get('GMOpen'), g.get('Resetting'), g.get('Completed'), g.not_(g.get('Initialized')))
    yes, no = g.branch(blocked)
    yes.engine('Actor', 'DisableInput', self=yes.get('Player'), PlayerController=yes.get('Controller'))
    movement = yes.get('CharacterMovement', yes.get('Player'), '/Script/Engine.Character')
    yes.engine('MovementComponent', 'StopMovementImmediately', self=movement)
    stop_weapon(yes)
    no.engine('Actor', 'EnableInput', self=no.get('Player'), PlayerController=no.get('Controller'))
    g.tail = (yes.tail if isinstance(yes.tail, list) else [yes.tail]) + [no.tail]
    g.set('bShowMouseCursor', g.get('GMOpen'), g.get('Controller'), PC)
    menu, game = g.branch(g.get('GMOpen'))
    menu.call('/Script/UMG.WidgetBlueprintLibrary.SetInputMode_GameAndUIEx',
              PlayerController=menu.get('Controller'), InMouseLockMode='DoNotLock',
              bHideCursorDuringCapture=False, bFlushInput=False)
    game.call('/Script/UMG.WidgetBlueprintLibrary.SetInputMode_GameOnly',
              PlayerController=game.get('Controller'), bFlushInput=False)

    g = g_('EnterRemote')
    ready(g)
    g.guard(g.not_(g.get('RemoteActive')))
    g.guard(g.valid(g.get('Monitor')))
    g.guard(g.or_(g.get('AccessCollected'), g.param('BypassAccess')))
    g.set('SavedView', g.engine('Controller', 'GetControlRotation', 'ReturnValue', self=g.get('Controller')))
    g.set('RemoteActive', True)
    g.set('HackedOnce', True)
    g.set('GMOpen', False)
    g.engine('PlayerController', 'SetViewTargetWithBlend', self=g.get('Controller'), NewViewTarget=g.get('Monitor'), BlendTime=0.15)
    g.call('RefreshControls')
    g.call('UpdateExit')
    g.set('StatusText', 'REMOTE LINK. Turn the camera away from the corridor. E / Q returns to your body.')
    g.log('OFFAIR_REMOTE_ENTER')

    g = g_('ExitRemote')
    g.guard(g.get('RemoteActive'))
    g.set('RemoteActive', False)
    g.guard(g.valid(g.get('Controller')))
    g.guard(g.valid(g.get('Player')))
    g.engine('PlayerController', 'SetViewTargetWithBlend', self=g.get('Controller'), NewViewTarget=g.get('Player'), BlendTime=0.15)
    g.engine('Controller', 'SetControlRotation', self=g.get('Controller'), NewRotation=g.get('SavedView'))
    g.call('RefreshControls')
    g.set('StatusText', 'BACK IN YOUR BODY. The camera keeps its new direction until the next loop.')
    g.log('OFFAIR_REMOTE_EXIT')

    g = g_('ToggleGM')
    ready(g)
    g.guard(session(g, 'GMEnabled'))
    g.set('GMOpen', g.not_(g.get('GMOpen')))
    g.call('RefreshControls')

    g = g_('TickRemote')
    ready(g)
    g.guard(g.get('RemoteActive'))
    yes, no = g.branch(g.valid(g.get('Monitor')))
    no.call('ExitRemote')
    no.set('StatusText', 'CAMERA SIGNAL LOST. Returned to body. R restores the device.')
    g.tail = yes.tail
    g.guard(g.not_(g.get('GMOpen')))
    mouse = g.engine('PlayerController', 'GetInputMouseDelta', self=g.get('Controller'))
    g.call('PanRemote', DeltaX=pin(mouse, 'DeltaX', True), DeltaY=pin(mouse, 'DeltaY', True))

    g = g_('PanRemote')
    ready(g)
    g.guard(g.and_(g.get('RemoteActive'), g.not_(g.get('GMOpen')), g.valid(g.get('Monitor'))))
    yaw = g.math('Add_DoubleDouble', A=g.get('RemoteYaw'), B=g.math('Multiply_DoubleDouble', A=g.param('DeltaX'), B=0.25))
    pitch = g.math('Subtract_DoubleDouble', A=g.get('RemotePitch'), B=g.math('Multiply_DoubleDouble', A=g.param('DeltaY'), B=0.25))
    g.set('RemoteYaw', g.engine('KismetMathLibrary', 'FClamp', 'ReturnValue', Value=yaw, Min=80.0, Max=280.0))
    g.set('RemotePitch', g.engine('KismetMathLibrary', 'FClamp', 'ReturnValue', Value=pitch, Min=-45.0, Max=5.0))
    g.engine('Actor', 'K2_SetActorRotation', self=g.get('Monitor'), NewRotation=g.rot(g.get('RemotePitch'), g.get('RemoteYaw')), bTeleportPhysics=True)

    g = g_('UpdateExit')
    open_ = g.and_(g.get('AccessCollected'), g.get('HackedOnce'), g.not_(g.get('Alarm')))
    show_actor(g, g.get('ExitGate'), g.not_(open_))

    g = g_('TickSurveillance')
    ready(g)
    g.guard(g.eq(g.get('Stage'), 1))
    g.guard(g.not_(g.get('Alarm')))
    g.guard(g.valid(g.get('Monitor')))
    player_pos = location(g, g.get('Player'))
    xyz = g.engine('KismetMathLibrary', 'BreakVector', InVec=player_pos)
    x, y = pin(xyz, 'X', True), pin(xyz, 'Y', True)
    in_zone = g.and_(g.math('Greater_DoubleDouble', A=x, B=2220.0), g.math('Less_DoubleDouble', A=x, B=3350.0),
                     g.math('Less_DoubleDouble', A=g.engine('KismetMathLibrary', 'Abs', 'ReturnValue', A=y), B=190.0))
    camera_pos = location(g, g.get('Monitor'))
    target = g.math('Add_VectorVector', A=player_pos, B=g.vec(0.0, 0.0, 45.0))
    offset = g.math('Subtract_VectorVector', A=target, B=camera_pos)
    direction = g.engine('KismetMathLibrary', 'Normal', 'ReturnValue', A=offset, Tolerance=0.0001)
    forward = g.engine('Actor', 'GetActorForwardVector', 'ReturnValue', self=g.get('Monitor'))
    cone = g.math('Greater_DoubleDouble', A=g.math('Dot_VectorVector', A=direction, B=forward), B=0.78)
    distance_ok = g.math('Less_DoubleDouble', A=g.engine('KismetMathLibrary', 'VSize', 'ReturnValue', A=offset), B=1450.0)
    # The controller LOS query accepts an explicit viewpoint: surveillance tests
    # the player's BODY from the camera position, including world occlusion.
    clear = g.engine('Controller', 'LineOfSightTo', 'ReturnValue', self=g.get('Controller'), Other=g.get('Player'), ViewPoint=camera_pos, bAlternateChecks=False)
    yes, no = g.branch(g.and_(in_zone, cone, distance_ok, clear))
    no.set('DetectionTime', 0.0)
    yes.set('DetectionTime', yes.math('Add_DoubleDouble', A=yes.get('DetectionTime'), B=yes.param('Delta')))
    yes.guard(yes.math('GreaterEqual_DoubleDouble', A=yes.get('DetectionTime'), B=0.4))
    yes.set('Alarm', True)
    yes.set('StatusText', 'ALARM: route sealed for this loop. Press R, then turn the camera farther away.')
    yes.call('UpdateExit')
    yes.log('OFFAIR_ALARM')

    g = g_('CheckFinish')
    ready(g)
    g.guard(g.and_(g.eq(g.get('Stage'), 1), g.get('AccessCollected'), g.get('HackedOnce'), g.not_(g.get('Alarm')), g.not_(g.get('RemoteActive'))))
    xyz = g.engine('KismetMathLibrary', 'BreakVector', InVec=location(g, g.get('Player')))
    g.guard(g.math('Greater_DoubleDouble', A=pin(xyz, 'X', True), B=3500.0))
    g.set('Completed', True)
    g.set('GMOpen', False)
    g.set('ObjectiveText', 'OFFAIR / LOOP BROKEN')
    g.set('StatusText', 'PROTOTYPE COMPLETE. You escaped using the camera blind spot. R starts again.')
    g.call('RefreshControls')
    g.log('OFFAIR_COMPLETE')


def build_tick():
    g = g_('GMAction')
    ready(g)
    g.guard(session(g, 'GMEnabled'))
    actions = [('KillPlayer', {}), ('GMStage', {'Delta': 1}), ('GMStage', {'Delta': -1}),
               ('GMAdd', {}), ('GMRemove', {}), ('EnterRemote', {'BypassAccess': True})]
    for index, (name, args) in enumerate(actions):
        g.when(g.eq(g.param('Action'), index), lambda b, n=name, a=args: b.call(n, **a))

    g = g_('TickInput')
    g.guard(g.valid(g.get('Controller')))
    g.guard(g.valid(g.get('Session')))
    g.guard(g.not_(g.get('Resetting')))
    g.guard(g.get('Initialized'))
    def close_disabled_menu(b):
        b.set('GMOpen', False)
        b.call('RefreshControls')
    g.when(g.and_(g.get('GMOpen'), g.not_(session(g, 'GMEnabled'))), close_disabled_menu)
    local(g, 'TickRemote', Delta=g.param('Delta'))
    local(g, 'TickSurveillance', Delta=g.param('Delta'))
    g.set('PollElapsed', g.math('Add_DoubleDouble', A=g.get('PollElapsed'), B=g.param('Delta')))
    def poll(b):
        b.set('PollElapsed', 0.0)
        b.call('PollEnemies')
    g.when(g.math('GreaterEqual_DoubleDouble', A=g.get('PollElapsed'), B=0.15), poll)
    local(g, 'CheckFinish')
    local(g, 'UpdateFeedback')

    g = g_('UpdateFeedback')
    ready(g)
    g.set('PromptText', '')
    stage0, stage1 = g.branch(g.eq(g.get('Stage'), 0))
    stage0.set('ObjectiveText', 'LOOP 0 / SECURE THE CYAN ANCHOR')
    stage0.when(stage0.math('EqualEqual_NameName', A=stage0.get('ConditionEvent'), B='EnemyKilled'),
                lambda b: b.set('ObjectiveText', 'LOOP 0 / DEFEAT THE KEY GUARD'))
    stage0.when(stage0.get('CoreCollected'), lambda b: b.set('ObjectiveText', 'ANCHOR LOCKED / PRESS R TO REWIND'))
    core_near = stage0.and_(stage0.not_(stage0.get('CoreCollected')),
        stage0.math('EqualEqual_NameName', A=stage0.get('ConditionEvent'), B='ItemAcquired'),
        stage0.call('CanInteract', 'Result', Target=stage0.get('CoreItem')))
    stage0.when(core_near, lambda b: b.set('PromptText', '[E] Secure anchor'))
    stage1.set('ObjectiveText', 'LOOP 1 / ARM YOURSELF AND DEFEAT THE GUARD')
    stage1.when(stage1.get('GuardRewarded'), lambda b: b.set('ObjectiveText', 'LOOP 1 / TAKE THE CARD TO THE TERMINAL'))
    stage1.when(stage1.get('AccessCollected'), lambda b: b.set('ObjectiveText', 'LOOP 1 / TURN THE CAMERA, THEN REACH THE EXIT'))
    access_near = stage1.and_(stage1.get('GuardRewarded'), stage1.not_(stage1.get('AccessCollected')), stage1.call('CanInteract', 'Result', Target=stage1.get('AccessItem')))
    stage1.when(access_near, lambda b: b.set('PromptText', '[E] Collect access card'))
    stage1.when(stage1.call('CanInteract', 'Result', Target=stage1.get('Terminal')), lambda b: b.set('PromptText', '[E] Connect to surveillance camera (access card required)'))
    stage1.when(stage1.get('RemoteActive'), lambda b: b.set('PromptText', 'MOUSE: turn camera     [E / Q] Return to body'))
    stage1.when(stage1.get('Alarm'), lambda b: b.set('ObjectiveText', 'ALARM / EXIT LOCKED / R TO RETRY'))


def build_events():
    # Custom event declarations must exist before functions can call them.
    g = Graph(BP['director'], 'EventGraph')
    g.event('FinalizeRun', False)
    g.event('ReloadWorld', False)
    compile_bp(BP['director'])


def finish_events():
    g = Graph(BP['director'], 'EventGraph')
    nodes = {str(n.get_node_title()): n for n in g.editor.list_all_nodes()}
    g.tail = nodes['FinalizeRun'].find_then_pin()
    item_condition = g.math('EqualEqual_NameName', A=g.get('ConditionEvent'), B='ItemAcquired')
    combat_condition = g.math('EqualEqual_NameName', A=g.get('ConditionEvent'), B='EnemyKilled')
    combat_stage = g.or_(g.eq(g.get('Stage'), 1), combat_condition)
    show_actor(g, g.get('CoreItem'), g.and_(g.eq(g.get('Stage'), 0), item_condition), False)
    show_actor(g, g.get('AccessItem'), False, False)
    show_actor(g, g.get('WeaponPickup'), combat_stage)
    show_actor(g, g.get('StageGate'), g.and_(g.eq(g.get('Stage'), 0), item_condition))
    show_actor(g, g.get('ExitGate'), True)
    g.set('RemoteYaw', 180.0)
    g.set('RemotePitch', -18.0)
    g.engine('Actor', 'K2_SetActorRotation', self=g.get('Monitor'), NewRotation=g.rot(-18.0, 180.0), bTeleportPhysics=True)
    set_session(g, 'ResetTarget', g.get('Stage'))
    set_session(g, 'ResetBusy', True)
    g.set('Initialized', True)
    g.when(combat_stage, lambda b: b.call('AddEnemy', KeyGuard=True))
    g.call('CommitRun')

    g = Graph(BP['director'], 'EventGraph')
    g.tail = nodes['ReloadWorld'].find_then_pin()
    g.engine('KismetSystemLibrary', 'Delay', Duration=0.65)
    g.engine('GameplayStatics', 'OpenLevel', LevelName=MAP, bAbsolute=True, Options='')

    g = Graph(BP['director'], 'EventGraph')
    g.event('ReceiveBeginPlay')
    g.engine('KismetSystemLibrary', 'Delay', Duration=0.15)
    local(g, 'InitializeRun')
    g = Graph(BP['director'], 'EventGraph')
    event = g.event('ReceiveTick')
    local(g, 'TickInput', Delta=pin(event, 'DeltaSeconds', True))

    # Override only the template's automatic respawn; inherited FPS input/HUD remain.
    g = Graph(BP['controller'], 'EventGraph')
    g.event('OnDestroyed_Event')
    g.log('OFFAIR_TEMPLATE_RESPAWN_SUPPRESSED')
    g = Graph(BP['mode'], 'EventGraph')
    g.event('ReceiveBeginPlay')
    g.log('OFFAIR_MODE_READY')  # suppress the arena scoreboard/local-player creation
    g = Graph(BP['player'], 'EventGraph')
    g.event('Die')
    director = g.engine('GameplayStatics', 'GetActorOfClass', 'ReturnValue', ActorClass=PATH['director'])
    director = g.cast(director, PATH['director'])
    g.call(PATH['director'] + ':AcceptDeath', self=director)


def build_controller_input():
    """Bind consumed key events on the controller, including while the pawn is disabled."""
    bp = BP['controller']
    editor = EDITOR.get_graph_editor_by_name(bp, 'EventGraph')
    available = [str(a) for a in editor.list_available_nodes([])]
    bindings = {'E': 'Interact', 'Q': 'ExitRemote', 'F1': 'ToggleGM', 'R': 'Restart'}
    bindings.update({str(i + 1): 'GMAction' for i in range(6)})
    for display, function in bindings.items():
        choices = [a for a in available if 'Keyboard' in a and a.rsplit('|', 1)[-1] == display]
        if len(choices) != 1:
            raise RuntimeError(f'Keyboard event not found for {display}: {choices}')
        g = Graph(bp, 'EventGraph')
        event = g.own(editor.create_node_from_name(choices[0], u.Vector2D(0, 0), [], None))
        if event.get_class().get_name() != 'K2Node_InputKey':
            raise RuntimeError('Unexpected keyboard node type: ' + event.get_class().get_name())
        g.tail = pin(event, 'Pressed', True)
        d = g.engine('GameplayStatics', 'GetActorOfClass', 'ReturnValue', ActorClass=PATH['director'])
        d = g.cast(d, PATH['director'])
        g.guard(g.valid(d))
        if function == 'GMAction':
            g.guard(g.get('GMOpen', d, PATH['director']))
            g.call(PATH['director'] + ':GMAction', self=d, Action=int(display)-1)
        elif function == 'Restart':
            normal, failed = g.branch(g.get('Initialized', d, PATH['director']))
            normal.call(PATH['director'] + ':Restart', self=d)
            s = failed.get('Session', d, PATH['director'])
            failed.guard(failed.valid(s))
            target = failed.get('ResetTarget', s, PATH['session'])
            failed.call(PATH['director'] + ':RequestReset', self=d, Target=target)
        else:
            g.call(PATH['director'] + ':' + function, self=d)


def set_defaults():
    compile_bp(BP['session'])
    s = u.get_default_object(generated_class(BP['session']))
    s.set_editor_property('PendingStage', -1)
    s.set_editor_property('GMEnabled', True)
    d = u.get_default_object(generated_class(BP['director']))
    d.set_editor_property('MaxEnemies', 8)
    d.set_editor_property('ConditionEvent', 'ItemAcquired')
    d.set_editor_property('ConditionTarget', 'Anchor')
    tick = d.get_editor_property('primary_actor_tick')
    tick.set_editor_property('start_with_tick_enabled', True)
    d.set_editor_property('primary_actor_tick', tick)
    mode = u.get_default_object(generated_class(BP['mode']))
    mode.set_editor_property('default_pawn_class', generated_class(BP['player']))
    mode.set_editor_property('player_controller_class', generated_class(BP['controller']))
    mode.set_editor_property('hud_class', generated_class(BP['hud']))
    pc = u.get_default_object(generated_class(BP['controller']))
    pc.set_editor_property('enable_click_events', True)


build_events()
build_core()
build_interactions()
build_remote()
build_tick()
finish_events()
build_controller_input()
from prototype_hud import build_hud
build_hud(BP, PATH)
for bp in BP.values():
    compile_bp(bp)
set_defaults()
for bp in BP.values():
    save(bp)
from prototype_level import build_level
build_level({k: generated_class(v) for k, v in BP.items()}, OUT)
(OUT / 'build-result.json').write_text(json.dumps({'blueprints': [bp.get_path_name() for bp in BP.values()], 'compiled': True}, indent=2), encoding='utf-8')
u.log('OFFAIR_BUILD_COMPLETE')
