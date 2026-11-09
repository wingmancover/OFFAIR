"""Offscreen PIE visual review of the saved layout. Never takes desktop input.

Run with -RenderOffscreen -ExecutePythonScript=<this file>. Captures are engine
game-viewport images, not desktop screenshots. The script does not save assets.
"""
import json
import time
import traceback
from pathlib import Path
import unreal as u

OUT=Path(__file__).resolve().parents[2]/'Saved/TwoRoomLayout'
LEVELS=u.get_editor_subsystem(u.LevelEditorSubsystem)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
shots=[('spawn',(400,1800,100),(0,0,0)),
       ('tutorial',(1100,1800,100),(0,0,0)),
       ('corridor',(4900,1800,100),(0,0,0)),
       ('puzzle',(6100,3200,100),(0,45,0)),
       ('dome',(6600,3400,100),(65,25,0)),
       ('overlook',(10400,4400,100),(0,0,0))]
index=0
phase='wait'
entered=time.monotonic()
started=entered
handle=None
busy=False
report={'status':'running','captures':[],'method':'RenderOffscreen PIE HighResShot; no desktop input'}


def finish(error=None):
    report['status']='failed' if error else 'passed'
    report['error']=error
    (OUT/'visual-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    u.unregister_slate_post_tick_callback(handle)
    LEVELS.editor_request_end_play()
    u.EditorPythonScripting.set_keep_python_script_alive(False)
    u.SystemLibrary.quit_editor()


def tick(dt):
    global busy,phase,entered,index
    if busy:
        return
    busy=True
    try:
        if time.monotonic()-started>180:
            raise TimeoutError('Visual capture timeout')
        world=UE.get_game_world()
        if not world:
            return
        pawn=u.GameplayStatics.get_player_pawn(world,0)
        pc=u.GameplayStatics.get_player_controller(world,0)
        if not pawn or not pc:
            return
        if phase=='wait':
            if time.monotonic()-entered<8:
                return
            phase='position'
        if phase=='position':
            name,pos,rotation=shots[index]
            pawn.set_actor_location(u.Vector(*pos),False,True)
            pawn.character_movement.stop_movement_immediately()
            pc.set_control_rotation(u.Rotator(pitch=rotation[0],yaw=rotation[1],roll=rotation[2]))
            entered=time.monotonic()
            phase='settle'
        elif phase=='settle' and time.monotonic()-entered>3:
            name=shots[index][0]
            dest=OUT/(name+'.png')
            dest.unlink(missing_ok=True)
            u.SystemLibrary.execute_console_command(world,'HighResShot 1600x900 filename="'+str(dest).replace('\\','/')+'"')
            entered=time.monotonic()
            phase='save'
        elif phase=='save' and time.monotonic()-entered>2:
            name=shots[index][0]
            dest=OUT/(name+'.png')
            if not dest.exists():
                raise RuntimeError('Missing screenshot '+str(dest))
            report['captures'].append(str(dest))
            index+=1
            if index==len(shots):
                finish()
                return
            phase='position'
    except Exception:
        finish(traceback.format_exc())
    finally:
        busy=False


assert LEVELS.load_level('/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout')
u.SystemLibrary.execute_console_command(UE.get_editor_world(),'MAP CHECK')
u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
LEVELS.editor_request_begin_play()
