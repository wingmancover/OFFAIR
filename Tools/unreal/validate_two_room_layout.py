"""Step-1 geometry/navigation and real CharacterMovement PIE checks.

Run in a separate hidden editor with -NullRHI -ExecutePythonScript=<this file>.
This drives movement programmatically, not keyboard input. It never saves PIE
objects or changes the user's existing prototype. Output is in Saved/TwoRoomLayout.
"""
import json
import math
import time
import traceback
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/TwoRoomLayout'
MAP='/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout'
LEVELS=u.get_editor_subsystem(u.LevelEditorSubsystem)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
REPORT={'status':'running','checks':[], 'movement_method':'Character.add_movement_input; not OS keyboard', 'corridor_seconds':None}
started=time.monotonic()
state='prepare'
handle=None
waypoint=0
entered=0
corridor_start=None
game_elapsed=0.0
busy=False
points=[(800,1800),(1500,1800),(2200,1800),(3000,1600),(4000,1800),
        (4800,1800),(6000,1800),(6000,2600),(6000,3300),(6200,3800),
        (6200,3100),(7400,3100),(8300,3100),(8300,4400),(9200,4400),(10400,4400)]


def v(point,z=100):
    return u.Vector(point[0],point[1],z)


def check(name, ok, detail=None):
    REPORT['checks'].append({'name':name,'passed':bool(ok),'detail':detail})
    if not ok:
        raise AssertionError(name+': '+str(detail))


def write():
    (OUT/'validation-result.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')


def finish(error=None):
    REPORT['status']='failed' if error else 'passed'
    REPORT['error']=error
    REPORT['elapsed_wall_seconds']=round(time.monotonic()-started,2)
    write()
    if handle is not None:
        u.unregister_slate_post_tick_callback(handle)
    LEVELS.editor_request_end_play()
    u.EditorPythonScripting.set_keep_python_script_alive(False)
    u.SystemLibrary.quit_editor()


def trace(world,a,b):
    hit=u.SystemLibrary.line_trace_single(world,u.Vector(*a),u.Vector(*b),u.TraceTypeQuery.TRACE_TYPE_QUERY1,
        False,[],u.DrawDebugTrace.NONE,True)
    return bool(hit and hit.to_tuple()[0])


def step(dt):
    global state,waypoint,entered,corridor_start,game_elapsed
    try:
        if time.monotonic()-started>200:
            raise TimeoutError('Layout validation exceeded 200 seconds')
        if state=='prepare':
            if time.monotonic()-started<3:
                return
            state='building_navigation'
            world=UE.get_editor_world()
            u.SystemLibrary.execute_console_command(world,'BUILDPATHS')
            entered=time.monotonic()
            return
        if state=='building_navigation':
            if time.monotonic()-entered<5:
                return
            world=UE.get_editor_world()
            actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
            labels={a.get_actor_label():a for a in actors}
            check('Both rooms and corridor authored',all(n in labels for n in ['OA_TutorialFloor','OA_PuzzleFloor','OA_CorridorEast','OA_CorridorNorth']))
            for label,expected in [('OA_TutorialFloor',(4800,3600)),('OA_PuzzleFloor',(3600,3600))]:
                _,e=labels[label].get_actor_bounds(False)
                check(label+' dimensions',abs(e.x*2-expected[0])<1 and abs(e.y*2-expected[1])<1,[e.x*2,e.y*2])
            data=u.GameplayStatics.get_all_actors_of_class(world,u.RecastNavMesh)
            check('Recast data exists',len(data)==1,len(data))
            nav=data[0]
            nav.set_editor_property('runtime_generation',u.RuntimeGenerationType.DYNAMIC)
            projections=[]
            for p in [(400,1800),(1500,1800),(3600,2800),(3600,800),(4800,1800),(6000,1800),
                      (6000,2400),(6200,3800),(8300,3100),(9200,4400),(10400,4400)]:
                q=u.NavigationSystemV1.project_point_to_navigation(world,v(p,40),nav,None,u.Vector(100,100,200))
                check('Navigation '+str(p),q is not None,str(q))
                projections.append([q.x,q.y,q.z])
            REPORT['navigation_projections']=projections
            # Collision checks at player-eye height and vertical no-roof samples.
            check('Corner occludes premature puzzle view',trace(world,(4600,1800,170),(6600,3800,170)))
            check('Tutorial has no local roof',not trace(world,(800,1800,200),(800,1800,3000)))
            check('Puzzle has no local roof',not trace(world,(6200,3800,200),(6200,3800,3000)))
            check('Camera C1 line of sight',not trace(world,(4000,1800,170),(4265,2665,320)))
            check('Camera C2 line of sight',not trace(world,(6200,3800,170),(7370,4275,320)))
            check('Platform outside edge blocks',trace(world,(10800,4400,170),(11200,4400,170)))
            for asset in ['/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter','/Game/FirstPerson/Blueprints/BP_FirstPersonPlayerController','/Game/FirstPerson/Blueprints/BP_FirstPersonGameMode']:
                check('Preview dependency compiles '+asset,u.BlueprintEditorLibrary.compile_blueprint(u.load_asset(asset)))
            check('Save map with navigation',LEVELS.save_current_level())
            state='wait_pie'
            LEVELS.editor_request_begin_play()
            entered=time.monotonic()
            write()
            return
        world=UE.get_game_world()
        if not world:
            return
        pawn=u.GameplayStatics.get_player_pawn(world,0)
        if not pawn:
            return
        if state=='wait_pie':
            if time.monotonic()-entered<1:
                return
            check('Preview pawn is template first person',pawn.get_class().get_name()=='BP_FirstPersonCharacter_C',pawn.get_class().get_name())
            check('Walk speed 600cm/s',abs(pawn.character_movement.max_walk_speed-600)<1)
            pos=pawn.get_actor_location()
            check('Spawn A',math.hypot(pos.x-400,pos.y-1800)<10,[pos.x,pos.y,pos.z])
            check('No old director in new map',not u.GameplayStatics.get_all_actors_of_class(world,u.load_class(None,'/Game/OFFAIR/Core/BP_RunDirector.BP_RunDirector_C')))
            state='walk'
            entered=time.monotonic()
        if state=='walk':
            # Engine delta, so background throttling does not count as walking time.
            game_elapsed+=u.GameplayStatics.get_world_delta_seconds(world)
            pos=pawn.get_actor_location()
            target=points[waypoint]
            dx,dy=target[0]-pos.x,target[1]-pos.y
            distance=math.hypot(dx,dy)
            if distance<22:
                check('Walk waypoint '+str(waypoint),-5<pos.z<180,[round(pos.x,1),round(pos.y,1),round(pos.z,1)])
                if waypoint==5:
                    corridor_start=game_elapsed
                if waypoint==7:
                    REPORT['corridor_seconds']=round(game_elapsed-corridor_start,3)
                    check('Corridor traverses in 3-4s simulation time',3.0<=REPORT['corridor_seconds']<=4.1,REPORT['corridor_seconds'])
                waypoint+=1
                entered=time.monotonic()
                if waypoint==len(points):
                    pawn.character_movement.stop_movement_immediately()
                    check('Continuous route reaches overlook',True)
                    finish()
                    return
                target=points[waypoint]
                dx,dy=target[0]-pos.x,target[1]-pos.y
                distance=math.hypot(dx,dy)
                write()
            if time.monotonic()-entered>30:
                raise RuntimeError('Movement blocked at waypoint '+str(waypoint)+' '+str(pos))
            pawn.add_movement_input(u.Vector(dx/distance,dy/distance,0),1,False)
    except Exception:
        finish(traceback.format_exc())


def tick(dt):
    global busy
    if busy:
        return
    busy=True
    try:
        step(dt)
    finally:
        busy=False


OUT.mkdir(parents=True,exist_ok=True)
assert LEVELS.load_level(MAP)
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
