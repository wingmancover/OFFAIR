"""Validate an ordinary editor launch and its inherited RunUAT environment.

Do not inject SDK variables here: the project editor module must establish them.
Compile existing project Blueprints in memory; never regenerate or save assets.
"""
import json
import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import traceback
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Saved/EditorRebuild"
OUT.mkdir(parents=True, exist_ok=True)
report = {"status": "failed", "checks": [], "blueprints": []}


def process_environment(name):
    # Embedded Python may initialize os.environ before the project module.
    # Read the actual Win32 environment inherited by UE's native RunUAT calls.
    get_value = ctypes.WinDLL("kernel32", use_last_error=True).GetEnvironmentVariableW
    get_value.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    get_value.restype = wintypes.DWORD
    buffer = ctypes.create_unicode_buffer(32768)
    length = get_value(name, buffer, len(buffer))
    assert length < len(buffer), "Environment variable exceeded the test buffer"
    return buffer.value


try:
    sdk = ROOT / "Saved/Toolchains/Program Files/dotnet"
    assert Path(process_environment("DOTNET_ROOT")).resolve() == sdk.resolve(), "Ordinary editor launch did not select the project SDK"
    assert process_environment("UE_USE_SYSTEM_DOTNET") == "1", "RunUAT would replace the selected SDK"
    assert len(process_environment("PATH")) < 8000, "Editor PATH still exceeds the Windows batch budget"
    report["path_length"] = len(process_environment("PATH"))
    report["checks"].append("ordinary_editor_configures_toolchain")
    engine = Path(u.Paths.convert_relative_path_to_full(u.Paths.engine_dir()))
    args = [str(engine / "Build/BatchFiles/RunUAT.bat"), f"-ScriptsForProject={ROOT / 'OFFAIR.uproject'}",
            "BuildUserSolution", f"-Project={ROOT / 'OFFAIR.uproject'}", f"-ScriptDir={ROOT}",
            "-TargetType=Editor", "-TargetConfiguration=Development", "-TargetPlatform=Win64",
            f"-OutputPath={ROOT / 'Binaries/Managed/net10.0'}"]
    with (OUT / "editor-uat.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    assert result.returncode == 0, f"Editor RunUAT failed: {result.returncode}"
    report["checks"].append("editor_run_uat_rebuild_succeeds")
    assert u.load_class(None, "/Script/UnrealSharp.OffairScriptProbe_C") is not None, "Managed class missing"
    report["checks"].append("managed_class_loaded")
    for path in sorted((ROOT / "Content/OFFAIR").rglob("BP_*.uasset")):
        asset_path = "/Game/" + path.relative_to(ROOT / "Content").with_suffix("").as_posix()
        blueprint = u.load_asset(asset_path)
        assert blueprint is not None and u.BlueprintEditorLibrary.compile_blueprint(blueprint), asset_path
        report["blueprints"].append(asset_path)
    report["checks"].append("project_blueprints_compile")
    report["status"] = "passed"
except Exception:
    report["error"] = traceback.format_exc()
finally:
    (OUT / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    u.log("OFFAIR_EDITOR_REBUILD_RESULT " + report["status"])
