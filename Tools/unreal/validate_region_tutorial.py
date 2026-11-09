"""Step 3 background PIE integration. Real projectile/AI/movement simulation;
interaction input is dispatched to the runtime handler, not physical OS keys.
Does not save gameplay state. Rebuilds/saves only editor navigation before PIE.
"""
import json,time,traceback
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parents[2]/'Saved/RegionTutorial'
L=u.get_editor_subsystem(u.LevelEditorSubsystem); UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
BASE='/Game/OFFAIR/Region/'
report={'status':'running','checks':[],'input':'Runtime handler + real simulated AI/projectiles; physical keys pending user'}
busy=False; handle=None; wait=0.; started=time.monotonic()
d=p=pc=w=None; actors={}
def check(n,v,detail=None):
    report['checks'].append(dict(name=n,passed=bool(v),detail=detail))
    (OUT/'validation-progress.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if not v:raise AssertionError(n+': '+str(detail))
def prop(n):return d.get_editor_property(n)
def call(n,*a):return d.call_method(n,a)
def key(n):call('HandleRegionInput',n)
def pos(x,y,z=100):
    p.set_actor_location(u.Vector(x,y,z),False,True);p.character_movement.stop_movement_immediately()
def look(a):
    target=a.get_actor_bounds(False)[0] if isinstance(a,u.Actor) else a
    eye=p.get_component_by_class(u.CameraComponent).get_world_location()
    pc.set_control_rotation(u.MathLibrary.find_look_at_rotation(eye,target))
def guards():return [a for a in u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,BASE+'BP_RegionGuard.BP_RegionGuard_C')) if a.get_editor_property('Current HP')>0]
def kill(a):u.GameplayStatics.apply_damage(a,10000,pc,p,u.DamageType)
def gm(n):
    if not prop('GMOpen'):key('F1')
    key(n)
    if prop('GMOpen'):key('F1')
def freeze(a):
    c=a.get_controller()
    if c:
        brain=c.get_component_by_class(u.BrainComponent)
        if brain:brain.stop_logic('Automated projectile accuracy fixture')
        c.stop_movement()
    a.call_method('Stop Shooting',());a.character_movement.stop_movement_immediately()
def run():
    global d,p,pc,w,actors
    assert L.load_level('/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout')
    ew=UE.get_editor_world();u.SystemLibrary.execute_console_command(ew,'BUILDPATHS');yield 4
    nav=u.GameplayStatics.get_all_actors_of_class(ew,u.RecastNavMesh)[0]
    nav.set_editor_property('runtime_generation',u.RuntimeGenerationType.DYNAMIC)
    for point in [(1270,1200),(1270,2400),(3600,2800),(3600,800),(4050,3200),(4050,400),(4350,2850),(4350,750),(6000,1800),(6000,3300)]:
        q=u.NavigationSystemV1.project_point_to_navigation(ew,u.Vector(*point,40),nav,None,u.Vector(100,100,200))
        check('Walkable '+str(point),q is not None)
    check('Navigation saved',L.save_current_level())
    for name in ['BP_RegionLoopDirector','BP_RegionShooterCharacter','BP_RegionBullet','BP_RegionAmberPistol','BP_RegionCyanPistol','BP_RegionGuardPistol','BP_RegionGuard','BP_RegionHUD','BP_RegionGameMode']:
        check(name+' compiles',u.BlueprintEditorLibrary.compile_blueprint(u.load_asset(BASE+name)))
    L.editor_request_begin_play();yield 3
    w=UE.get_game_world();d=u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,BASE+'BP_RegionLoopDirector.BP_RegionLoopDirector_C'))[0]
    p=u.GameplayStatics.get_player_character(w,0);pc=u.GameplayStatics.get_player_controller(w,0)
    unarmed=[(m,m.get_editor_property('anim_class')) for m in p.get_components_by_class(u.SkeletalMeshComponent)]
    report['initial_animation_classes']=[str(c) for m,c in unarmed]
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    check('Initialized without setup error',prop('Initialized') and not prop('FailureText'),prop('FailureText'))
    check('Shooter pawn reused','RegionShooter' in p.get_class().get_name())
    check('GM hidden / no guards',not prop('GMOpen') and not guards())
    report['initial_ai_controllers']=[a.get_name() for a in u.GameplayStatics.get_all_actors_of_class(w,u.AIController)]
    key('Two');key('R');check('Hidden GM / R do nothing',not prop('HasGun') and prop('AttemptId')==1)
    pos(1270,1200);look(actors['OA_G2_Weapon']);yield .3
    key('E');check('Gun unavailable before first memory',not prop('HasGun'))
    pos(9000,4400);look(actors['OA_MemoryB_Case']);yield .3;key('E')
    check('B rejects missing prerequisites',not prop('CheckpointSaved'))
    pos(600,1800);look(actors['OA_RedNote']);yield .3
    key('E');check('First note starts three-second lock',prop('Transition')==1 and pc.is_move_input_ignored())
    key('E');key('R');yield 1
    check('No early loop from repeated input',prop('AttemptId')==1 and prop('Transition')==1)
    yield 3
    check('First death returns A with memory',prop('MemoryExperienced') and prop('DeathCount')==1 and prop('Transition')==0)
    check('Note and guns restored',not actors['OA_RedNote'].get_editor_property('hidden') and not prop('HasGun'))
    pos(1050,1200);look(actors['OA_G2_Weapon']);yield .3;key('E')
    check('Gun rejects excessive range',not prop('HasGun'))
    pos(1270,1200);pc.set_control_rotation(u.Rotator(yaw=180));yield .3;key('E')
    check('Gun rejects looking away',not prop('HasGun'))
    blocker=u.OffairScriptTestLibrary.spawn_test_actor(w,u.StaticMeshActor)
    blocker.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
    blocker.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
    blocker.set_actor_scale3d(u.Vector(.2,1.5,2));blocker.set_actor_location(u.Vector(1380,1200,100),False,True)
    look(actors['OA_G2_Weapon']);yield .3;key('E')
    check('Gun rejects occluding wall',not prop('HasGun'));blocker.destroy_actor()
    pos(1270,1200);look(actors['OA_G2_Weapon']);yield .3
    key('E');yield .3
    check('Cyan equips weapon and spawns two guards',prop('HasGun') and prop('ChosenWeapon')==2 and len(guards())==2,prop('FailureText'))
    check('One inventory weapon',len(p.get_editor_property('Owned Weapons'))==1)
    check('Picking up a gun switches the player pose',any(m.get_editor_property('anim_class')!=c for m,c in unarmed))
    key('E');check('Repeated pickup does not spawn duplicate wave',len(guards())==2)
    # Actual navigation and attacks, rather than manufacturing damage against the player.
    initial=[a.get_actor_location() for a in guards()];hp=prop('Health')
    pos(3100,2800);yield 2
    for _ in range(10):
        yield 1
        if prop('Health')<hp:break
    check('Guard AI attacks player',prop('Health')<hp,{'before':hp,'after':prop('Health'),'guards':[str(a.get_actor_location()) for a in guards()]})
    check('Guard AI moves on navigation',any((a.get_actor_location()-b).length()>50 for a,b in zip(guards(),initial)))
    gs=guards();check('Two-guard fight remains alive for test',len(gs)==2 and prop('Transition')==0)
    for a in gs:freeze(a)
    # Fire the real weapon at a stationary live guard. Damage must come from projectile hits.
    pos(2600,1800);gs[0].set_actor_location(u.Vector(3100,1800,100),False,True)
    gs[1].set_actor_location(u.Vector(3600,2800,100),False,True);yield .3
    before=gs[0].get_editor_property('Current HP');look(gs[0]);yield .3
    call('SetRegionFiring',True);yield .35;call('SetRegionFiring',False);yield .3
    check('Real player projectile damages guard',gs[0].get_editor_property('Current HP')<before,gs[0].get_editor_property('Current HP'))
    check('Ammo reduced by actual shot',prop('Ammo')<10,prop('Ammo'))
    for _ in range(5):
        if gs[0].get_editor_property('Current HP')<=0:break
        look(gs[0]);yield .1;call('SetRegionFiring',True);yield .3;call('SetRegionFiring',False);yield .15
    check('First guard defeated using actual pistol shots',gs[0].get_editor_property('Current HP')<=0)
    yield .3
    check('No card before complete wave',prop('KilledGuards')==1 and not prop('CardDropped'))
    kill(gs[0]);yield .2;check('Repeated dead-guard event counted once',prop('KilledGuards')==1)
    gs[1].set_actor_location(u.Vector(3100,2050,100),False,True)
    for _ in range(6):
        if gs[1].get_editor_property('Current HP')<=0:break
        look(gs[1]);yield .1;call('SetRegionFiring',True);yield .3;call('SetRegionFiring',False);yield .15
    check('Second guard defeated using actual pistol shots',gs[1].get_editor_property('Current HP')<=0)
    yield .3
    check('Last kill drops one card',prop('LivingGuards')==0 and prop('KilledGuards')==2 and prop('CardDropped'))
    gm('Four');yield .2;check('GM cannot restart combat after card drop',not guards())
    card=actors['OA_CameraAccessCard'];cp=card.get_actor_location();pos(cp.x-220,cp.y);look(card);yield .3
    key('E');check('E collects card',prop('HasAccessCard') and card.get_editor_property('hidden'))
    pos(2000,2350);look(actors['OA_C1_Housing']);yield .3;key('E')
    check('Camera rejects beyond 20m',not prop('RemoteActive'))
    pos(4000,2350);look(actors['OA_C1_Housing']);yield .3
    key('E');check('Aim/E enters C1',prop('RemoteActive'),prop('PromptText'))
    key('Q');check('Exit without turning cannot complete lesson',not prop('CameraLearned'))
    yield .2;look(actors['OA_C1_Housing']);yield .3;key('E')
    camera=actors['OA_C1_Camera'];pitch=camera.get_actor_rotation().pitch
    call('PanTutorialCamera',60.,20.)
    check('Camera upward input increases pitch',camera.get_actor_rotation().pitch>pitch)
    key('E');check('Turn plus normal exit learns camera and opens D1',prop('CameraLearned') and not actors['OA_TutorialGate'].get_actor_enable_collision())
    check('Body view and input restored',not prop('RemoteActive') and not pc.is_move_input_ignored() and pc.get_view_target()==p)
    pos(4500,1800)
    for target in [u.Vector(5100,1800,100),u.Vector(6000,1800,100),u.Vector(6000,2800,100)]:
        for _ in range(300):
            delta=target-p.get_actor_location();delta.z=0
            if delta.length()<65:break
            p.add_movement_input(delta.normal(),1,False);yield 0
        check('Actual movement through D1 / corridor '+str(target),delta.length()<65,str(p.get_actor_location()))
    old=prop('AttemptId');gm('One');call('RequestRegionDeath',old);yield 1
    check('One death per attempt / stale event rejected',prop('AttemptId')==old+1 and not call('ReportRegionProgress',old,1))
    check('Death resets all unsaved tutorial state',not prop('HasGun') and not prop('HasAccessCard') and not prop('CameraLearned') and not prop('CardDropped') and not guards())
    check('Both guns / gate / camera baseline restored',not actors['OA_G1_Weapon'].get_editor_property('hidden') and not actors['OA_G2_Weapon'].get_editor_property('hidden') and actors['OA_TutorialGate'].get_actor_enable_collision() and abs(camera.get_actor_rotation().yaw+135)<.1)
    check('Destroyed weapons removed from inventory',len(p.get_editor_property('Owned Weapons'))==0)
    check('GM death restores first and third person unarmed animation',all(m.get_editor_property('anim_class')==c for m,c in unarmed))
    ais=u.GameplayStatics.get_all_actors_of_class(w,u.AIController)
    check('No orphan AI controllers after death',not ais,[a.get_name() for a in ais])
    check('No old projectiles after death',not u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,BASE+'BP_RegionBullet.BP_RegionBullet_C')))
    pos(1270,2400);look(actors['OA_G1_Weapon']);yield .3;key('E');yield .3
    check('Amber equips and spawns ten guards',prop('ChosenWeapon')==1 and len(guards())==10)
    gm('Four');yield .2;check('GM adds guard',len(guards())==11)
    gm('Five');yield .2;check('GM removal does not count / invalidates reward',len(guards())==10 and prop('KilledGuards')==0 and not prop('WaveRewardEligible'))
    for a in guards():kill(a)
    yield .4;check('GM removal cannot produce card after clearing',not prop('CardDropped'))
    gm('One');yield 1
    check('Knowledge thought suggests other gun','cyan' in prop('ThoughtText').lower())
    check('Amber retry restores unarmed animation',all(m.get_editor_property('anim_class')==c for m,c in unarmed))
    # Ten real guard instances; test-only damage isolates the amber victory branch from aim skill.
    pos(1270,2400);look(actors['OA_G1_Weapon']);yield .3;key('E');yield .2
    for a in guards():freeze(a)
    for a in guards()[:9]:kill(a)
    yield .3;check('Amber nine kills is not a victory',prop('KilledGuards')==9 and not prop('CardDropped') and 'Ten guards' not in prop('HostText'))
    kill(guards()[0]);yield .3
    check('Amber tenth kill drops card and plays exclusive praise',prop('KilledGuards')==10 and prop('CardDropped') and 'Ten guards' in prop('HostText'),prop('HostText'))
    gm('One');yield 1
    # Fire into a wall, then reset while the template's wiggle/delayed physics effect is active.
    for choice in [2,1]:
        pos(1270,1200 if choice==2 else 2400);look(actors['OA_G2_Weapon' if choice==2 else 'OA_G1_Weapon']);yield .3;key('E');yield .2
        for a in guards():freeze(a)
        pos(4500,1800);look(u.Vector(4800,1800,170));yield .3
        for _ in range(4):
            call('SetRegionFiring',True);yield .3;call('SetRegionFiring',False);yield .1
        gm('One');yield 4.5
        check('Wall-hit projectiles cleaned after '+str(choice)+' gun reset',not u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,BASE+'BP_RegionBullet.BP_RegionBullet_C')))
        check('Pose remains unarmed after delayed hit effects '+str(choice),all(m.get_editor_property('anim_class')==c for m,c in unarmed))
    # A genuine projectile delivers the lethal hit, exercising reset reentrantly inside EventHit.
    pos(1270,1200);look(actors['OA_G2_Weapon']);yield .3;key('E');yield .2
    gs=guards()
    for a in gs:freeze(a)
    pos(3100,2800);gs[0].set_actor_location(u.Vector(3500,2800,100),False,True)
    call('ApplyRegionDamage',prop('Health')-25,prop('AttemptId'));old=prop('AttemptId')
    gs[0].call_method('Start Shooting',(p,))
    for _ in range(60):
        yield .1
        if prop('AttemptId')!=old:break
    check('Real lethal projectile triggers death',prop('AttemptId')==old+1)
    yield 4.5
    check('Combat death restores unarmed pose and clears projectiles',prop('Transition')==0 and all(m.get_editor_property('anim_class')==c for m,c in unarmed) and not u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,BASE+'BP_RegionBullet.BP_RegionBullet_C')))
    gm('Six');check('GM camera bypass does not grant access',prop('RemoteActive') and not prop('HasAccessCard'))
    call('PanTutorialCamera',80.,0.);gm('One');yield 1
    check('Death in camera restores body without lesson reward',not prop('RemoteActive') and not prop('CameraLearned') and pc.get_view_target()==p and not pc.is_move_input_ignored())
    gm('Seven');c2=actors['OA_C2_Camera']
    check('C2 starts away from answer',abs(c2.get_actor_rotation().yaw-20)<.1 and c2.get_actor_rotation().pitch<0)
    call('PanTutorialCamera',200.,80.);key('Q')
    check('C2 preview does not complete C1 lesson',not prop('CameraLearned'))
    gm('One');yield 1
    check('C2 resets after unsaved death',abs(c2.get_actor_rotation().yaw-20)<.1)
    gm('Two');check('Explicit GM B setup supplies real weapon',prop('DebugPrepared') and len(p.get_editor_property('Owned Weapons'))==1)
    gm('Three');yield .3;key('E')
    check('B save requires explicit E',prop('CheckpointSaved'),prop('ThoughtText'))
    gm('One');yield 1
    check('B death keeps progress and restores equipped gun',prop('CheckpointSaved') and prop('HasGun') and prop('HasAccessCard') and len(p.get_editor_property('Owned Weapons'))==1 and p.get_actor_location().x>9000)
    check('B restore retains the armed pose for its saved weapon',any(m.get_editor_property('anim_class')!=c for m,c in unarmed))
    check('B does not reclose completed teaching room',not actors['OA_TutorialGate'].get_actor_enable_collision())
    L.editor_request_end_play();yield 1;L.editor_request_begin_play();yield 3
    w=UE.get_game_world();d=u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,BASE+'BP_RegionLoopDirector.BP_RegionLoopDirector_C'))[0]
    check('Fresh PIE clears session memory/save',not prop('MemoryExperienced') and not prop('CheckpointSaved'))
    p=u.GameplayStatics.get_player_character(w,0);pc=u.GameplayStatics.get_player_controller(w,0)
    gm('Six');prop('TutorialCamera').destroy_actor();yield .3
    check('Invalid camera returns to body without reward',not prop('RemoteActive') and pc.get_view_target()==p and not prop('CameraLearned'))
    gm('One');yield 1
    check('Missing baseline actor fails closed',prop('Transition')==2 and 'baseline' in prop('FailureText').lower())

def finish(error=None):
    report.update(status='failed' if error else 'passed',error=error,seconds=round(time.monotonic()-started,2))
    (OUT/'validation-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    u.unregister_slate_post_tick_callback(handle);L.editor_request_end_play()
    u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
job=run()
def tick(dt):
    global busy,wait
    if busy:return
    busy=True
    try:
        if time.monotonic()-started>240:raise TimeoutError('Step 3 verification')
        wait-=dt
        if wait<=0:wait=next(job)
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
OUT.mkdir(parents=True,exist_ok=True)
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
