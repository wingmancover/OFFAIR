"""Rebuild/save this map's nav data; verify walkable surfaces and D2 collision in PIE.
CharacterMovement input is simulated, not OS keyboard. Main editor must be on another map.
"""
import json,time,traceback
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parents[2]/'Saved/RegionLoop'
L=u.get_editor_subsystem(u.LevelEditorSubsystem); UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
state='build'; entered=time.monotonic(); started=entered; busy=False; handle=None
report={'status':'running','checks':[]}; d=None; p=None; pc=None; index=0
points=[(800,1800),(1500,1800),(2200,1800),(3000,1600),(4000,1800),(4800,1800),(6000,1800),(6000,2600),(6000,3300),(6200,3800),(6200,3100),(7400,3100),(8300,3100),(8500,4400)]
def check(n,v,detail=None):
    report['checks'].append({'name':n,'passed':bool(v),'detail':detail})
    if not v:raise AssertionError(n+': '+str(detail))
def finish(error=None):
    report.update(status='failed' if error else 'passed',error=error)
    (OUT/'navigation-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    u.unregister_slate_post_tick_callback(handle);L.editor_request_end_play()
    u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
def tick(dt):
    global busy,state,entered,d,p,pc,index
    if busy:return
    busy=True
    try:
        if time.monotonic()-started>170:raise TimeoutError(state)
        if state=='build':
            state='nav';u.SystemLibrary.execute_console_command(UE.get_editor_world(),'BUILDPATHS');entered=time.monotonic();return
        if state=='nav' and time.monotonic()-entered>4:
            w=UE.get_editor_world();navs=u.GameplayStatics.get_all_actors_of_class(w,u.RecastNavMesh)
            check('Recast generated',len(navs)==1)
            navs[0].set_editor_property('runtime_generation',u.RuntimeGenerationType.DYNAMIC)
            for xy in points+[(9200,4400),(10400,4400)]:
                q=u.NavigationSystemV1.project_point_to_navigation(w,u.Vector(*xy,40),navs[0],None,u.Vector(100,100,200))
                check('Walkable '+str(xy),q is not None)
            check('Saved rebuilt navigation',L.save_current_level())
            state='wait';L.editor_request_begin_play();return
        w=UE.get_game_world()
        if not w:return
        if state=='wait':
            ds=u.GameplayStatics.get_all_actors_of_class(w,u.load_class(None,'/Game/OFFAIR/Region/BP_RegionLoopDirector.BP_RegionLoopDirector_C'))
            if not ds or not ds[0].get_editor_property('Initialized'):return
            d=ds[0];p=u.GameplayStatics.get_player_character(w,0);pc=u.GameplayStatics.get_player_controller(w,0)
            state='walk'
        if state=='walk':
            x,y=points[index]; delta=u.Vector(x,y,p.get_actor_location().z)-p.get_actor_location()
            if delta.length()<70:
                check('Walked waypoint '+str(index),True);index+=1
                if index==len(points):state='closed';entered=time.monotonic()
            else:p.add_movement_input(delta.normal(),1,False)
        elif state=='closed':
            p.add_movement_input(u.Vector(1,0,0),1,False)
            if time.monotonic()-entered>1.3:
                check('Closed D2 blocks player',p.get_actor_location().x<8780,p.get_actor_location().x)
                # Real note interaction first, then explicit debug prerequisite preparation.
                p.set_actor_location(u.Vector(600,1800,100),False,True)
                pc.set_control_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(600,1800,164),u.Vector(800,1800,1)))
                state='note';entered=time.monotonic()
        elif state=='note' and time.monotonic()-entered>.2:
            d.call_method('HandleRegionInput',('E',));state='reset';entered=time.monotonic()
        elif state=='reset' and time.monotonic()-entered>4:
            check('Memory death completed',d.get_editor_property('MemoryExperienced'))
            d.call_method('HandleRegionInput',('F1',));d.call_method('HandleRegionInput',('Two',))
            p.set_actor_location(u.Vector(8500,4400,100),False,True)
            state='open';entered=time.monotonic()
        elif state=='open':
            p.add_movement_input(u.Vector(1,0,0),1,False)
            if p.get_actor_location().x>9150:
                check('Opened D2 allows actual movement to B',True)
                finish()
            elif time.monotonic()-entered>5:raise AssertionError('Opened gate still blocks player')
    except Exception:finish(traceback.format_exc())
    finally:busy=False
assert L.load_level('/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout')
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
