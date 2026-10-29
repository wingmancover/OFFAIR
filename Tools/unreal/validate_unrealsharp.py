"""Build and exercise a Blueprint child of a C# Actor in two PIE sessions.

The fixture is isolated under /Game/OFFAIR/Tests. No prototype assets are saved.
Actual gameplay regressions remain in validate_prototype.py.
"""
import json
from pathlib import Path
import sys
import time
import traceback
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from graph_builder import Graph, create_bp, declare, generated_class, pin, put, save

OUTPUT = ROOT / "Saved/UnrealSharpTests/result.json"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
# Upstream creates a CSClass with the _C suffix in its global managed package.
# Its editor-only owning Blueprint is in the C# namespace package instead.
MANAGED = "/Script/UnrealSharp.OffairScriptProbe_C"
FIXTURE = "/Game/OFFAIR/Tests/BP_UnrealSharpProbe"
LEVEL = "/Game/OFFAIR/Levels/Lvl_Prototype"
DIRECTOR_PATH = "/Game/OFFAIR/Core/BP_RunDirector.BP_RunDirector_C"
EDITOR = u.get_editor_subsystem(u.LevelEditorSubsystem)
UE = u.get_editor_subsystem(u.UnrealEditorSubsystem)
state = {"status": "running", "passed": [], "phase": "first", "started": time.monotonic()}
handle = None
probe_class = None
director_class = None


def write():
    OUTPUT.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def passed(name):
    state["passed"].append(name)
    u.log("OFFAIR_CSHARP_PASS " + name)
    write()


def finish(status, error=""):
    state.update(status=status, error=error, elapsed_seconds=round(time.monotonic() - state["started"], 2))
    write()
    if handle is not None:
        u.unregister_slate_post_tick_callback(handle)
    EDITOR.editor_request_end_play()
    u.EditorPythonScripting.set_keep_python_script_alive(False)


def exercise(world, label):
    require(not u.GameplayStatics.get_all_actors_of_class(world, probe_class), "Old managed actor survived reset")
    actor = u.OffairScriptTestLibrary.spawn_test_actor(world, probe_class)
    require(actor is not None, "Could not spawn the Blueprint child of the managed Actor")
    require(int(actor.get_editor_property("CallCount")) == 0, "Managed state leaked into a fresh actor")
    require(actor.call_method("BlueprintRoundTrip", (41,)) == 42, "Blueprint -> C# -> Blueprint return failed")
    require(int(actor.get_editor_property("CallCount")) == 1, "Managed reflected property was not updated")
    require(actor.call_method("BlueprintRoundTrip", (-1,)) == 0, "Second call failed")
    require(int(actor.get_editor_property("CallCount")) == 2, "Instance state did not persist within its world")
    passed(label)


def tick(delta):
    try:
        require(time.monotonic() - state["started"] < 120, "UnrealSharp smoke test timed out")
        world = UE.get_game_world()
        if state["phase"] == "between_sessions":
            if world is None:
                state["phase"] = "second"
                EDITOR.editor_request_begin_play()
            return
        if world is None:
            return
        director = u.GameplayStatics.get_actor_of_class(world, director_class)
        if not director or not director.get_editor_property("Initialized") or director.get_editor_property("Resetting"):
            return
        session = director.get_editor_property("Session")
        if state["phase"] == "first":
            exercise(world, "blueprint_calls_managed_actor")
            state["run"] = int(session.get_editor_property("RunNumber"))
            state["phase"] = "after_death"
            director.call_method("KillPlayer", ())
        elif state["phase"] == "after_death":
            if int(session.get_editor_property("RunNumber")) <= state["run"]:
                return
            require(int(director.get_editor_property("Stage")) == 0, "Death without a condition advanced the stage")
            exercise(world, "managed_instance_resets_after_death_map_reload")
            state["phase"] = "between_sessions"
            EDITOR.editor_request_end_play()
        elif state["phase"] == "second":
            exercise(world, "managed_instance_resets_in_second_pie_session")
            finish("passed")
    except Exception:
        finish("failed", traceback.format_exc())


try:
    u.EditorPythonScripting.set_keep_python_script_alive(True)
    require(u.load_class(None, MANAGED) is not None, "Managed UClass did not load: " + MANAGED)
    passed("managed_uclass_registered")
    bp = create_bp(FIXTURE, MANAGED)
    declare(bp, "BlueprintRoundTrip", {"Value": "int"}, {"Result": "int"})
    graph = Graph(bp, "BlueprintRoundTrip")
    value = graph.call(MANAGED + ".RoundTrip", "ReturnValue", value=graph.param("Value"))
    result_node = next(node for node in graph.editor.list_all_nodes()
                       if node.get_class().get_name() == "K2Node_FunctionResult")
    put(pin(result_node, "Result"), value)
    graph.wire_exec(result_node)
    save(bp)
    probe_class = generated_class(bp)
    director_class = u.load_class(None, DIRECTOR_PATH)
    passed("blueprint_child_compiles_and_saves")
    require(EDITOR.load_level(LEVEL), "Prototype map could not load")
    handle = u.register_slate_post_tick_callback(tick)
    EDITOR.editor_request_begin_play()
    write()
except Exception:
    finish("failed", traceback.format_exc())
