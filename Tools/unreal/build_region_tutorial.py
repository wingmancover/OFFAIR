"""Step 3 incremental author: reuse shooter weapons, projectile damage, NPC StateTree AI.
Run after managed-build, with the main editor on a different map. Does not rebuild rooms.
"""
import json, math, sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from graph_builder import Graph, create_bp, declare, generated_class, pin, save, compile_bp
import build_region_loop as region
import build_two_room_layout as layout
BASE=region.BASE
MANAGED=region.MANAGED
SHOOTER='/Game/Variant_Shooter/Blueprints/BP_ShooterCharacter.BP_ShooterCharacter_C'
NPC='/Game/Variant_Shooter/Blueprints/AI/BP_ShooterNPC.BP_ShooterNPC_C'
WEAPON='/Game/Variant_Shooter/Blueprints/Pickups/BP_ShooterWeaponBase.BP_ShooterWeaponBase_C'
PISTOL='/Game/Variant_Shooter/Blueprints/Pickups/Weapons/BP_ShooterWeapon_Pistol.BP_ShooterWeapon_Pistol_C'
BULLET='/Game/Variant_Shooter/Blueprints/Pickups/Projectiles/BP_ShooterProjectile_Bullet.BP_ShooterProjectile_Bullet_C'
PROJECTILE='/Game/Variant_Shooter/Blueprints/Pickups/Projectiles/BP_ShooterProjectileBase.BP_ShooterProjectileBase_C'
ACTOR='/Script/Engine.Actor'; CHARACTER='/Script/Engine.Character'
ASSETS=u.get_editor_subsystem(u.EditorAssetSubsystem)
ACTORS=u.get_editor_subsystem(u.EditorActorSubsystem)
LEVELS=u.get_editor_subsystem(u.LevelEditorSubsystem)
OUT=ROOT/'Saved/RegionTutorial'

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    bp=u.load_asset(BASE+'/BP_RegionLoopDirector')
    director_path=bp.get_path_name()+'_C'
    player=create_bp(BASE+'/BP_RegionShooterCharacter',SHOOTER)
    region.clear_events(player)
    g=Graph(player,'EventGraph'); ev=g.event('ReceiveAnyDamage')
    d=g.engine('GameplayStatics','GetActorOfClass','ReturnValue',ActorClass=director_path)
    d=g.cast(d,MANAGED);g.guard(g.valid(d))
    g.call(MANAGED+':ApplyRegionDamage',self=d,Damage=pin(ev,'Damage',True),ExpectedAttempt=g.get('AttemptId',d,MANAGED))
    g=Graph(player,'EventGraph');g.event('Die')
    d=g.engine('GameplayStatics','GetActorOfClass','ReturnValue',ActorClass=director_path)
    d=g.cast(d,MANAGED);g.guard(g.valid(d))
    g.call(MANAGED+':RequestRegionDeath',self=d,ExpectedAttempt=g.get('AttemptId',d,MANAGED))
    save(player)

    bullet=create_bp(BASE+'/BP_RegionBullet',BULLET)
    region.clear_events(bullet)
    g=Graph(bullet,'EventGraph');g.event('ReceiveBeginPlay')
    instigator=g.engine('Actor','GetInstigator','ReturnValue')
    component=g.get('CollisionComponent')
    g.engine('PrimitiveComponent','IgnoreActorWhenMoving',self=component,Actor=instigator,bShouldIgnore=True)
    d=g.engine('GameplayStatics','GetActorOfClass','ReturnValue',ActorClass=director_path)
    d=g.cast(d,MANAGED);g.guard(g.valid(d))
    selfpin=g.engine('ActorComponent','GetOwner','ReturnValue',self=component)
    g.call(MANAGED+':RegisterTutorialProjectile',self=d,Projectile=selfpin,Shooter=instigator)
    save(bullet)

    weapons=[]
    for name in ['BP_RegionAmberPistol','BP_RegionCyanPistol','BP_RegionGuardPistol']:
        weapon=create_bp(BASE+'/'+name,PISTOL)
        cdo=u.get_default_object(generated_class(weapon))
        cdo.set_editor_property('Bullet Class',generated_class(bullet))
        save(weapon);weapons.append(weapon)
    guard=create_bp(BASE+'/BP_RegionGuard',NPC)
    u.get_default_object(generated_class(guard)).set_editor_property('Weapon Class',generated_class(weapons[2]))
    save(guard)

    # Keep functions on the managed director as small Blueprint adapters for template-specific members.
    declarations={
        'EquipTutorialWeapon':({'Holder':CHARACTER,'Choice':'int'},{'ReturnValue':ACTOR}),
        'ClearTutorialWeapon':({'Holder':CHARACTER},{}),
        'FireTutorialWeapon':({'Weapon':ACTOR,'Firing':'bool'},{}),
        'SpawnTutorialGuard':({'Transform':'/Script/CoreUObject.Transform'},{'ReturnValue':ACTOR}),
        'GetTutorialGuardHealth':({'Guard':ACTOR},{'ReturnValue':'real'}),
        'RemoveTutorialGuard':({'Guard':ACTOR},{}),
        'GetTutorialAmmo':({'Weapon':ACTOR},{'ReturnValue':'int'}),
    }
    for name in declarations:
        graph=u.BlueprintEditorLibrary.find_graph(bp,name)
        if graph:
            editor=u.BlueprintGraphEditor.get_graph_editor(graph)
            editor.remove_nodes([n for n in editor.list_all_nodes() if n.get_class().get_name() not in ('K2Node_FunctionEntry','K2Node_FunctionResult')])
        else:
            assert u.BlueprintEditorLibrary.add_function_override(bp,name),name
    compile_bp(bp)
    g=Graph(bp,'EquipTutorialWeapon');holder=g.cast(g.param('Holder'),SHOOTER)
    yes,no=g.branch(g.eq(g.param('Choice'),1))
    for b,w in [(yes,weapons[0]),(no,weapons[1])]:
        b.call(SHOOTER+':Add Weapon Class',self=holder,**{'Weapon Class':generated_class(w)})
        b.ret(ReturnValue=b.get('Current Weapon',holder,SHOOTER))
    g=Graph(bp,'ClearTutorialWeapon');holder=g.cast(g.param('Holder'),SHOOTER)
    items=g.get('Owned Weapons',holder,SHOOTER)
    body,item=g.foreach(items);body.guard(body.valid(item))
    body.call(WEAPON+':Stop Firing',self=item)
    body.engine('Actor','K2_DestroyActor',self=item)
    g.call('/Script/Engine.KismetArrayLibrary.Array_Clear',TargetArray=items)
    g.set('Current Weapon',None,holder,SHOOTER)
    g=Graph(bp,'FireTutorialWeapon');w=g.cast(g.param('Weapon'),WEAPON)
    yes,no=g.branch(g.param('Firing'))
    yes.call(WEAPON+':Start Firing',self=w);no.call(WEAPON+':Stop Firing',self=w)
    g=Graph(bp,'SpawnTutorialGuard')
    location=g.engine('KismetMathLibrary','BreakTransform','Location',InTransform=g.param('Transform'))
    target=g.engine('GameplayStatics','GetPlayerPawn','ReturnValue',PlayerIndex=0)
    target_location=g.engine('Actor','K2_GetActorLocation','ReturnValue',self=target)
    facing=g.engine('KismetMathLibrary','FindLookAtRotation','ReturnValue',Start=location,Target=target_location)
    yaw=g.engine('KismetMathLibrary','BreakRotator','Yaw',InRot=facing)
    # Template perception is directional: face the newly armed player, not the marker's +X axis.
    a=g.spawn(generated_class(guard),g.transform(location,g.rot(yaw=yaw)))
    g.guard(g.valid(a))
    movement=g.get('CharacterMovement',a,CHARACTER)
    g.set('MaxWalkSpeed',220.,movement,'/Script/Engine.CharacterMovementComponent')
    g.ret(ReturnValue=a)
    g=Graph(bp,'GetTutorialGuardHealth');a=g.cast(g.param('Guard'),NPC)
    g.ret(ReturnValue=g.get('Current HP',a,NPC))
    g=Graph(bp,'GetTutorialAmmo');a=g.cast(g.param('Weapon'),WEAPON)
    g.ret(ReturnValue=g.get('Current Bullets',a,WEAPON))
    g=Graph(bp,'RemoveTutorialGuard');a=g.cast(g.param('Guard'),NPC)
    g.call(NPC+':Stop Shooting',self=a)
    controller=g.engine('Pawn','GetController','ReturnValue',self=a)
    g.when(g.valid(controller),lambda b:b.engine('Actor','SetLifeSpan',self=controller,InLifespan=.01))
    g.engine('Actor','K2_DestroyActor',self=a)
    save(bp)

    # Runtime font caches rasterize at readable sizes instead of enlarging the tiny default canvas font.
    hud=u.load_asset(BASE+'/BP_RegionHUD');hcdo=u.get_default_object(generated_class(hud))
    for name,size,prop in [('F_RegionPlay',26,'PlayFont'),('F_RegionSmall',20,'SmallPlayFont')]:
        path=BASE+'/UI/'+name
        font=u.load_asset(path) if ASSETS.does_asset_exist(path) else ASSETS.duplicate_asset('/Engine/EngineFonts/Roboto',path)
        assert font
        font.set_editor_property('legacy_font_size',size)
        assert font.get_editor_property('font_cache_type')==u.FontCacheType.RUNTIME
        ASSETS.save_loaded_asset(font,False);hcdo.set_editor_property(prop,font)
    save(hud)
    mode=u.load_asset(BASE+'/BP_RegionGameMode')
    u.get_default_object(generated_class(mode)).set_editor_property('default_pawn_class',generated_class(player));save(mode)

    assert LEVELS.load_level(layout.MAP)
    actors={a.get_actor_label():a for a in ACTORS.get_all_level_actors()}
    for name in ['ivory','metal','amber','cyan']:
        layout.MATS[name]=u.load_asset(layout.MAT_DIR+'/M_Lay_'+name)
    def box(name,pos,size,material):
        a=actors.get('OA_'+name)
        if not a:
            a=layout.box(name,pos,size,material,folder='POI_Props')
            a.tags=list(a.tags)+['OFFAIR_REGION_STEP3'];actors['OA_'+name]=a
        a.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
        return a
    gate=box('TutorialGate',(4800,1800,250),(30,570,500),'ivory')
    card=box('CameraAccessCard',(3600,1800,65),(32,21,3),'amber')
    card.set_actor_hidden_in_game(True);card.set_actor_enable_collision(False)
    card.static_mesh_component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    for key,pos in [('E7',(4050,3200,100)),('E8',(4050,400,100)),
                    ('E9',(4350,2850,100)),('E10',(4350,750,100))]:
        if 'OA_POI_'+key not in actors:
            actors['OA_POI_'+key]=layout.poi(key,pos,'EnemySpawn','High pressure branch')
    c1=actors['OA_C1_Camera']
    c1.set_actor_location(u.Vector(4265,2665,320),False,False)
    c1.set_actor_rotation(u.Rotator(pitch=-12,yaw=225),False)
    c2=actors['OA_C2_Camera']
    c2.set_actor_location(u.Vector(7442,4315,320),False,False)
    c2.set_actor_rotation(u.Rotator(pitch=-15,yaw=20),False)
    actors['OA_C2_Housing'].set_actor_rotation(u.Rotator(yaw=20),False)
    actors['OA_C2_Lens'].set_actor_location(u.Vector(7432,4312,320),False,False)
    actors['OA_C2_Lens'].set_actor_rotation(u.Rotator(yaw=20),False)
    d=actors['OA_RegionLoopDirector']
    baseline=list(d.get_editor_property('BaselineActors'))
    for a in [gate,card]:
        if a not in baseline:baseline.append(a)
    for k,v in dict(AlternativeWeapon=actors['OA_G2_Weapon'],AccessCard=card,TutorialCamera=c1,
        TutorialCameraTarget=actors['OA_C1_Housing'],TutorialGate=gate,MaximumHealth=500.,BaselineActors=baseline,
        GuardSpawnPoints=[actors['OA_POI_E'+str(i)] for i in range(1,11)],
        CameraEnterSound=region.sound('S_CameraEnter',[(800,.08),(1200,.12)]),
        CameraExitSound=region.sound('S_CameraExit',[(1000,.08),(500,.12)])).items():d.set_editor_property(k,v)
    assert LEVELS.save_current_level()
    (OUT/'build-result.json').write_text(json.dumps({'status':'authored','map':layout.MAP,
        'compiled':[a.get_path_name() for a in [bp,player,bullet,*weapons,guard,hud,mode]],
        'guard_spawns':10,'player_maximum_health':500,'old_prototype_modified':False},indent=2),encoding='utf-8')
    u.log('OFFAIR_REGION_TUTORIAL_AUTHORED')

if __name__=='__main__':build()
