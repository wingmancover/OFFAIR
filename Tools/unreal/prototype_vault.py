"""Small, swept three-part vault for the dedicated prototype obstacle."""
import unreal as u
from graph_builder import Graph, member, declare, pin, pin_type


def declare_vault(bp):
    for name, kind in {'VaultObstacle':'/Script/Engine.Actor', 'VaultActive':'bool',
                       'VaultElapsed':'real', 'VaultStart':'/Script/CoreUObject.Vector',
                       'VaultEnd':'/Script/CoreUObject.Vector', 'VaultUpStart':'/Script/CoreUObject.Vector',
                       'VaultUpEnd':'/Script/CoreUObject.Vector'}.items():
        member(bp,name,kind)
    u.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(bp,'VaultObstacle',True)
    u.BlueprintEditorLibrary.set_blueprint_variable_category(bp,'VaultObstacle','Stage Setup')
    declare(bp,'CanVault',{}, {'Result':'bool'})
    declare(bp,'TryVault')
    declare(bp,'CancelVault')
    declare(bp,'TickVault',{'Delta':'real'})


def build_vault(bp):
    def graph(name):return Graph(bp,name)
    def loc(g,a):return g.engine('Actor','K2_GetActorLocation','ReturnValue',self=a)
    def add(g,a,b):return g.math('Add_VectorVector',A=a,B=b)
    def sub(g,a,b):return g.math('Subtract_VectorVector',A=a,B=b)
    def mul(g,a,b):return g.math('Multiply_VectorFloat',A=a,B=b)
    def z(g,v):return pin(g.engine('KismetMathLibrary','BreakVector',InVec=v),'Z',True)
    def move(g):return g.get('CharacterMovement',g.get('Player'),'/Script/Engine.Character')
    def forward(g):
        rot=g.engine('Controller','GetControlRotation','ReturnValue',self=g.get('Controller'))
        yaw=pin(g.engine('KismetMathLibrary','BreakRotator',InRot=rot),'Yaw',True)
        return g.engine('KismetMathLibrary','GetForwardVector','ReturnValue',InRot=g.rot(0.0,yaw,0.0))
    def ignored(g):
        if 'IgnoredActors' not in g.editor.list_local_variable_names():
            g.editor.add_local_variable('IgnoredActors',pin_type('array:/Script/Engine.Actor'),'')
        a=pin(g.own(g.editor.add_get_local_variable_node('IgnoredActors')),'IgnoredActors',True)
        g.call('/Script/Engine.KismetArrayLibrary.Array_Clear',TargetArray=a)
        g.call('/Script/Engine.KismetArrayLibrary.Array_Add',TargetArray=a,NewItem=g.get('Player'))
        return a
    def line(g,start,end,a):
        return g.engine('KismetSystemLibrary','LineTraceSingle',Start=start,End=end,TraceChannel='TraceTypeQuery1',
                        bTraceComplex=False,ActorsToIgnore=a,DrawDebugType='None',bIgnoreSelf=True)
    def capsule(g,start,end,a,radius,half):
        return g.engine('KismetSystemLibrary','CapsuleTraceSingle','ReturnValue',Start=start,End=end,
                        Radius=radius,HalfHeight=half,TraceChannel='TraceTypeQuery1',bTraceComplex=False,
                        ActorsToIgnore=a,DrawDebugType='None',bIgnoreSelf=True)

    g=graph('CanVault')
    reject=lambda b:b.ret(Result=False)
    g.guard(g.and_(g.get('Initialized'),g.not_(g.get('Resetting')),g.not_(g.get('Completed'))),reject)
    for name in ['VaultActive','RemoteActive','GMOpen','SystemResetActive']:
        g.guard(g.not_(g.get(name)),reject)
    g.guard(g.valid(g.get('Player')),reject)
    g.guard(g.valid(g.get('VaultObstacle')),reject)
    g.guard(g.engine('NavMovementComponent','IsMovingOnGround','ReturnValue',self=move(g)),reject)
    delta=sub(g,loc(g,g.get('VaultObstacle')),loc(g,g.get('Player')))
    delta=g.engine('KismetMathLibrary','Multiply_VectorVector','ReturnValue',A=delta,B='1,1,0')
    distance=g.engine('KismetMathLibrary','VSize','ReturnValue',A=delta)
    g.guard(g.math('LessEqual_DoubleDouble',A=distance,B=185.0),reject)
    direction=g.engine('KismetMathLibrary','Normal','ReturnValue',A=delta,Tolerance=0.0001)
    g.ret(Result=g.math('Greater_DoubleDouble',A=g.math('Dot_VectorVector',A=direction,B=forward(g)),B=0.8))

    g=graph('TryVault')
    g.guard(g.call('CanVault','Result'))
    a=ignored(g)
    start=loc(g,g.get('Player'))
    fwd=forward(g)
    hit=line(g,add(g,start,g.vec(0.0,0.0,-38.0)),add(g,add(g,start,g.vec(0.0,0.0,-38.0)),mul(g,fwd,185.0)),a)
    g.guard(pin(hit,'ReturnValue',True))
    info=g.engine('GameplayStatics','BreakHitResult',Hit=pin(hit,'OutHit',True))
    g.guard(g.math('EqualEqual_ObjectObject',A=pin(info,'HitActor',True),B=g.get('VaultObstacle')))
    bounds=g.engine('Actor','GetActorBounds',self=g.get('VaultObstacle'),bOnlyCollidingComponents=True,bIncludeFromChildActors=False)
    top=g.math('Add_DoubleDouble',A=z(g,pin(bounds,'Origin',True)),B=z(g,pin(bounds,'BoxExtent',True)))
    cap=g.get('CapsuleComponent',g.get('Player'),'/Script/Engine.Character')
    half=g.engine('CapsuleComponent','GetScaledCapsuleHalfHeight','ReturnValue',self=cap)
    radius=g.engine('CapsuleComponent','GetScaledCapsuleRadius','ReturnValue',self=cap)
    height=g.math('Subtract_DoubleDouble',A=top,B=g.math('Subtract_DoubleDouble',A=z(g,start),B=half))
    g.guard(g.and_(g.math('GreaterEqual_DoubleDouble',A=height,B=45.0),g.math('LessEqual_DoubleDouble',A=height,B=130.0)))
    ahead=add(g,start,mul(g,fwd,280.0))
    ground=line(g,add(g,ahead,g.vec(0.0,0.0,150.0)),add(g,ahead,g.vec(0.0,0.0,-180.0)),a)
    g.guard(pin(ground,'ReturnValue',True))
    floor=g.engine('GameplayStatics','BreakHitResult',Hit=pin(ground,'OutHit',True))
    g.guard(g.math('GreaterEqual_DoubleDouble',A=z(g,pin(floor,'ImpactNormal',True)),B=0.7))
    end=add(g,pin(floor,'ImpactPoint',True),g.vec(0.0,0.0,g.math('Add_DoubleDouble',A=half,B=3.0)))
    rise=g.math('Subtract_DoubleDouble',A=g.math('Add_DoubleDouble',A=top,B=g.math('Add_DoubleDouble',A=half,B=18.0)),B=z(g,start))
    upstart=add(g,start,g.vec(0.0,0.0,rise))
    upend=add(g,upstart,mul(g,fwd,280.0))
    for frm,to in [(start,upstart),(upstart,upend),(upend,end)]:
        g.guard(g.not_(capsule(g,frm,to,a,radius,half)))
    for name,value in [('VaultStart',start),('VaultEnd',end),('VaultUpStart',upstart),('VaultUpEnd',upend)]:g.set(name,value)
    g.set('VaultElapsed',0.0)
    g.set('VaultActive',True)
    g.call('RefreshControls')
    g.engine('CharacterMovementComponent','SetMovementMode',self=move(g),NewMovementMode='MOVE_Flying',NewCustomMode=0)
    g.log('OFFAIR_VAULT_START')

    g=graph('CancelVault')
    g.guard(g.get('VaultActive'))
    g.set('VaultActive',False)
    g.set('VaultElapsed',0.0)
    g.guard(g.valid(g.get('Player')))
    g.engine('MovementComponent','StopMovementImmediately',self=move(g))
    g.engine('CharacterMovementComponent','SetMovementMode',self=move(g),NewMovementMode='MOVE_Falling',NewCustomMode=0)
    g.call('RefreshControls')

    g=graph('TickVault')
    g.guard(g.get('VaultActive'))
    g.set('VaultElapsed',g.math('Add_DoubleDouble',A=g.get('VaultElapsed'),B=g.param('Delta')))
    def step(b,frm,to,offset,duration):
        alpha=b.engine('KismetMathLibrary','FClamp','ReturnValue',Value=b.math('Divide_DoubleDouble',A=b.math('Subtract_DoubleDouble',A=b.get('VaultElapsed'),B=offset),B=duration),Min=0.0,Max=1.0)
        point=b.engine('KismetMathLibrary','VLerp','ReturnValue',A=b.get(frm),B=b.get(to),Alpha=alpha)
        moved=b.engine('Actor','K2_SetActorLocation',self=b.get('Player'),NewLocation=point,bSweep=True,bTeleport=False)
        blocked=b.engine('GameplayStatics','BreakHitResult','bBlockingHit',Hit=pin(moved,'SweepHitResult',True))
        b.when(blocked,lambda c:c.call('CancelVault'))
    first,later=g.branch(g.math('Less_DoubleDouble',A=g.get('VaultElapsed'),B=0.2))
    step(first,'VaultStart','VaultUpStart',0.0,0.2)
    across,last=later.branch(later.math('Less_DoubleDouble',A=later.get('VaultElapsed'),B=0.6))
    step(across,'VaultUpStart','VaultUpEnd',0.2,0.4)
    step(last,'VaultUpEnd','VaultEnd',0.6,0.2)
    last.when(last.math('GreaterEqual_DoubleDouble',A=last.get('VaultElapsed'),B=0.8),lambda b:b.call('CancelVault'))


def update_vault_layout():
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    by_label={a.get_actor_label():a for a in actors.get_all_level_actors()}
    obstacle=by_label.get('OF_VaultObstacle')
    if not obstacle:
        obstacle=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(330,-330,55))
        obstacle.set_actor_label('OF_VaultObstacle')
        obstacle.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
        obstacle.set_actor_scale3d(u.Vector(0.6,2.2,1.1))
    obstacle.static_mesh_component.set_material(0,u.load_asset('/Game/OFFAIR/Materials/M_Anchor'))
    by_label['OF_RunDirector'].set_editor_property('VaultObstacle',obstacle)
    sign=by_label.get('OF_VaultSign')
    if not sign:
        sign=actors.spawn_actor_from_class(u.TextRenderActor,u.Vector(298,-330,160),u.Rotator(pitch=0,yaw=180,roll=0))
        sign.set_actor_label('OF_VaultSign')
        sign.text_render.set_text('VAULT TEST\n[V] VAULT')
        sign.text_render.set_world_size(20)
        sign.text_render.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
    sign.set_actor_rotation(u.Rotator(pitch=0,yaw=180,roll=0),True)
    sign.set_actor_location(u.Vector(298,-330,85),False,True)
    sign.text_render.set_world_size(7)
    sign.text_render.set_text_render_color(u.Color(10,20,30,255))
    return obstacle
