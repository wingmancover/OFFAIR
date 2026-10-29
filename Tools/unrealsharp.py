"""OFFAIR's pinned UnrealSharp toolchain. Requires Python 3.12+ and UE 5.8.

Run setup once, then build/editor/test/smoke/package. Generated files stay in
Unreal's ignored output folders. Only prototype-build regenerates gameplay assets.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "OFFAIR.uproject"
PLUGIN = ROOT / "Plugins" / "UnrealSharp"
LOCK = json.loads((ROOT / "Tools" / "unrealsharp.lock.json").read_text(encoding="utf-8"))
WINDOWS = sys.platform == "win32"


def host_target():
    if WINDOWS and platform.machine().lower() in ("amd64", "x86_64"):
        return "Win64", "x64", "win-x64"
    if sys.platform == "darwin" and platform.machine().lower() == "arm64":
        return "Mac", "arm64", "osx-arm64"
    raise RuntimeError("Supported build hosts: Windows x64 or native Apple Silicon macOS.")


def sdk_root():
    # The pinned plugin's Windows SDK locator matches 'Program Files\\dotnet\\'
    # in PATH. Keep this suffix locally instead of modifying the system SDK.
    suffix = Path("Program Files/dotnet") if WINDOWS else Path("dotnet")
    return ROOT / "Saved" / "Toolchains" / suffix


def run(args, env=None, cwd=ROOT):
    print("Running:", subprocess.list2cmdline([str(a) for a in args]), flush=True)
    subprocess.run([str(a) for a in args], cwd=cwd, env=env, check=True)


def check_plugin():
    if not (PLUGIN / "UnrealSharp.uplugin").is_file():
        raise RuntimeError("Run python Tools/unrealsharp.py setup to initialize UnrealSharp.")
    revision = subprocess.check_output(["git", "-C", str(PLUGIN), "rev-parse", "HEAD"], text=True).strip()
    if revision != LOCK["pluginRevision"]:
        raise RuntimeError(f"UnrealSharp revision mismatch: {revision}. Restore the pinned submodule.")


def setup():
    _, _, rid = host_target()
    if not (PLUGIN / "UnrealSharp.uplugin").exists():
        run(["git", "submodule", "update", "--init", "--recursive", "Plugins/UnrealSharp"])
    check_plugin()
    destination = sdk_root()
    executable = destination / ("dotnet.exe" if WINDOWS else "dotnet")
    if executable.exists() and (destination / "sdk" / LOCK["sdkVersion"]).is_dir():
        print("Pinned .NET SDK is already installed:", destination)
        return
    specification = LOCK["sdkArchives"][rid]
    cache = ROOT / "Saved" / "Toolchains"
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / specification["url"].rsplit("/", 1)[1]
    if not archive.exists():
        print("Downloading", specification["url"], flush=True)
        partial = archive.with_suffix(archive.suffix + ".partial")
        with urllib.request.urlopen(specification["url"], timeout=120) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output)
        partial.replace(archive)
    with archive.open("rb") as source:
        actual_hash = hashlib.file_digest(source, "sha512").hexdigest()
    if actual_hash != specification["sha512"]:
        raise RuntimeError(f"SDK SHA-512 mismatch; remove the invalid download: {archive}")
    destination.mkdir(parents=True, exist_ok=True)
    if WINDOWS:
        with zipfile.ZipFile(archive) as source:
            source.extractall(destination)
    else:
        with tarfile.open(archive) as source:
            source.extractall(destination, filter="data")
    run([executable, "--version"])


def environment():
    check_plugin()
    sdk = sdk_root()
    executable = sdk / ("dotnet.exe" if WINDOWS else "dotnet")
    if not executable.exists():
        raise RuntimeError("Pinned .NET SDK is missing. Run python Tools/unrealsharp.py setup.")
    env = os.environ.copy()
    env["DOTNET_ROOT"] = str(sdk)
    entries = [str(sdk) + os.sep, *env.get("PATH", "").split(os.pathsep)]
    if WINDOWS:
        # Keep RunUAT.bat below cmd.exe's environment-variable length limit.
        seen = set()
        valid_entries = []
        for entry in entries:
            entry = entry.strip()
            key = os.path.normcase(os.path.normpath(entry))
            if entry and Path(entry).is_dir() and key not in seen:
                seen.add(key)
                valid_entries.append(entry)
        entries = valid_entries
    env["PATH"] = os.pathsep.join(entries)
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"
    # Editor-triggered RunUAT must retain the same pinned SDK as this launcher.
    env["UE_USE_SYSTEM_DOTNET"] = "1"
    # Installed UE 5.8 builds may omit UE5Rules.csproj. Upstream's automation
    # props otherwise falls back to net8.0, which UE 5.8's UHT cannot load.
    # engine_root() rejects other engine versions before any build is launched.
    env["UE5Rules_DefineConstants"] = "UE_5_8_OR_LATER"
    # Upstream's macOS editor prefers this system path over PATH when it exists.
    mac_system = Path("/usr/local/share/dotnet")
    if not WINDOWS and mac_system.exists():
        runtimes = mac_system / "shared" / "Microsoft.NETCore.App"
        versions = [tuple(map(int, p.name.split("."))) for p in runtimes.glob("10.*")
                    if all(part.isdigit() for part in p.name.split("."))]
        if not versions or max(versions) < (10, 0, 5):
            raise RuntimeError("UnrealSharp prefers /usr/local/share/dotnet on Mac. Update that installation to .NET 10.0.5+ before launching the editor.")
    return env, executable


def engine_root(value):
    default = r"C:\Program Files\Epic Games\UE_5.8" if WINDOWS else "/Users/Shared/Epic Games/UE_5.8"
    engine = Path(value or os.environ.get("UE_ENGINE_ROOT", default)) / "Engine"
    version_file = engine / "Build" / "Build.version"
    if not version_file.exists():
        raise RuntimeError(f"UE not found at {engine.parent}; pass --engine-root or UE_ENGINE_ROOT.")
    version = json.loads(version_file.read_text(encoding="utf-8-sig"))
    if (version["MajorVersion"], version["MinorVersion"]) != (5, 8):
        raise RuntimeError("This integration is pinned to UE 5.8; engine upgrades need separate validation.")
    return engine


def uat(engine, dotnet, env, command, *arguments):
    run([dotnet, engine / "Binaries/DotNET/AutomationTool/AutomationTool.dll",
         f"-ScriptsForProject={PROJECT}", command, f"-Project={PROJECT}",
         f"-ScriptDir={ROOT}", *arguments], env, engine / "Source")


def build(engine, dotnet, env, disabled_plugins):
    target, architecture, _ = host_target()
    ubt = [dotnet, engine / "Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll"]
    exclusions = [f"-DisablePlugin={name}" for name in disabled_plugins]
    # UnrealSharp reads UE5Rules.csproj's version constants to select net10.0.
    run([*ubt, "-ProjectFiles", f"-Project={PROJECT}", "-Game", "-Engine", *exclusions],
        env, engine / "Source")
    run([*ubt,
         "OFFAIREditor", target, "Development", f"-Project={PROJECT}",
         f"-Architecture={architecture}", "-WaitMutex", "-NoHotReloadFromIDE", *exclusions], env, engine / "Source")
    uat(engine, dotnet, env, "BuildUserSolution", "-TargetType=Editor",
        "-TargetConfiguration=Development", f"-TargetPlatform={target}",
        f"-OutputPath={ROOT / 'Binaries/Managed/net10.0'}")


def editor(engine, env, mode):
    executable = engine / ("Binaries/Win64/UnrealEditor.exe" if WINDOWS else
                           "Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor")
    args = [executable, PROJECT]
    if mode != "editor":
        tasks = {
            "smoke": ("UnrealSharpTests", "validate_unrealsharp.py", "result.json"),
            "test": ("PrototypeTests", "validate_prototype.py", "runtime-result.json"),
            "editor-rebuild-test": ("EditorRebuild", "validate_editor_rebuild.py", "result.json"),
        }
        folder_name, script, result_name = tasks[mode]
        folder = ROOT / "Saved" / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        result = folder / result_name
        # Remove only the known previous report, so a crashed run cannot pass on stale evidence.
        result.unlink(missing_ok=True)
        args.extend(["-EnablePlugins=PythonScriptPlugin", "-unattended", "-nop4", "-nosound",
                     "-NullRHI", "-NoSplash", "-NoLiveCoding", f"-abslog={folder / 'run.log'}",
                     f"-ExecutePythonScript={ROOT / 'Tools/unreal' / script}"])
    run(args, env)
    if mode != "editor":
        report = json.loads(result.read_text(encoding="utf-8"))
        if report.get("status") != "passed":
            raise RuntimeError(f"{mode} failed: {report.get('error', report)}")
        print("Passed:", result)


def prototype_build(engine, env):
    folder = ROOT / "Saved/PrototypeBuild"
    folder.mkdir(parents=True, exist_ok=True)
    result = folder / "build-result.json"
    result.unlink(missing_ok=True)
    binary = engine / ("Binaries/Win64/UnrealEditor-Cmd.exe" if WINDOWS else
                       "Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor")
    common = [PROJECT, "-EnablePlugins=PythonScriptPlugin", "-unattended", "-nop4", "-nosound", "-NullRHI"]
    run([binary, *common, "-run=pythonscript", f"-script={ROOT / 'Tools/unreal/build_prototype.py'}",
         f"-abslog={folder / 'run.log'}"], env)
    binary = engine / ("Binaries/Win64/UnrealEditor.exe" if WINDOWS else
                       "Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor")
    run([binary, *common, "-NoSplash", f"-ExecutePythonScript={ROOT / 'Tools/unreal/finalize_navigation.py'}",
         f"-abslog={folder / 'navigation.log'}"], env)
    report = json.loads(result.read_text(encoding="utf-8"))
    if not report.get("compiled") or not report.get("navigation_ready"):
        raise RuntimeError(f"Prototype build is incomplete: {result}")
    print("Prototype build passed:", result)


def package(engine, dotnet, env, disabled_plugins):
    # Compile the editor separately so editor-only plugin exclusions do not
    # leak into the game's shared installed-engine build environment.
    build(engine, dotnet, env, disabled_plugins)
    target, architecture, _ = host_target()
    archive = ROOT / "Saved" / "Packages" / target
    uat(engine, dotnet, env, "BuildCookRun", "-noP4", "-nocompileeditor", "-build", "-cook", "-stage", "-pak",
        "-archive", f"-archivedirectory={archive}", f"-platform={target}",
        f"-architecture={architecture}", "-clientconfig=Development", "-utf8output",
        "-map=/Game/OFFAIR/Levels/Lvl_Prototype")
    # Managed binaries are relative to FPaths::ProjectDir, not the archive root.
    layouts = ("OFFAIR", "Windows/OFFAIR") if WINDOWS else (
        "OFFAIR.app/Contents/UE/OFFAIR", "Mac/OFFAIR.app/Contents/UE/OFFAIR")
    candidates = [archive / layout for layout in layouts if (archive / layout).is_dir()]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one packaged project under {archive}, found {candidates}; inspect the native archive before publishing managed files.")
    packaged_project = candidates[0]
    uat(engine, dotnet, env, "PackageProject", f"-ArchiveDirectory={packaged_project}",
        "-UETargetType=Game", "-UEBuildConfig=Development",
        f"-TargetPlatform={target}", f"-TargetArchitecture={architecture}")


def package_smoke():
    target, _, _ = host_target()
    archive = ROOT / "Saved/Packages" / target
    names = ("OFFAIR/Binaries/Win64/OFFAIR.exe", "Windows/OFFAIR/Binaries/Win64/OFFAIR.exe") if WINDOWS else (
        "OFFAIR.app/Contents/MacOS/OFFAIR", "Mac/OFFAIR.app/Contents/MacOS/OFFAIR")
    executables = [archive / name for name in names if (archive / name).is_file()]
    if len(executables) != 1:
        raise RuntimeError(f"Expected one packaged executable under {archive}, found {executables}")
    output = ROOT / "Saved/UnrealSharpPackageTests"
    output.mkdir(parents=True, exist_ok=True)
    log = output / "run.log"
    report_path = output / "result.json"
    log.unlink(missing_ok=True)
    report_path.unlink(missing_ok=True)
    # Exercise the bundled runtime, without the launcher's project-local SDK.
    env = {key: value for key, value in os.environ.items() if not key.startswith("DOTNET_ROOT")}
    env["PATH"] = os.pathsep.join(path for path in env.get("PATH", "").split(os.pathsep)
                                 if "dotnet" not in path.lower())
    command = [str(executables[0]), "-unattended", "-nullrhi", "-nosound",
               "-benchmark", "-seconds=4", "-fps=30", f"-abslog={log}"]
    print("Running:", subprocess.list2cmdline(command), flush=True)
    report = {"status": "failed", "platform": target, "command": command}
    try:
        subprocess.run(command, cwd=archive, env=env, check=True, timeout=120,
                       creationflags=subprocess.CREATE_NO_WINDOW if WINDOWS else 0)
        content = log.read_text(encoding="utf-8", errors="replace")
        checks = {
            "self_contained_runtime": "Runtime config is self-contained: true" in content,
            "project_assembly_loaded": bool(re.search(r"Successfully loaded assembly at .*Offair\.Managed\.dll", content)),
            "prototype_initialized": "OFFAIR_RUN_READY" in content,
            "no_runtime_errors": not re.search(r": Error:|Fatal error|Unhandled exception", content, re.IGNORECASE),
        }
        report["checks"] = checks
        if not all(checks.values()):
            raise RuntimeError(f"Packaged startup checks failed: {checks}; inspect {log}")
        report["status"] = "passed"
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        report["error"] = str(error)
        raise
    finally:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Packaged startup passed:", report_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["setup", "build", "editor", "test", "smoke", "package", "package-smoke", "prototype-build", "editor-rebuild-test"])
    parser.add_argument("--engine-root")
    parser.add_argument("--disable-plugin", action="append", default=[],
                        help="Exclude a plugin from the editor build (also before packaging); repeatable.")
    args = parser.parse_args()
    if args.disable_plugin and args.mode not in ("build", "package"):
        parser.error("--disable-plugin applies only to build and package")
    host_target()
    if args.mode == "setup":
        setup()
        return
    if args.mode == "package-smoke":
        package_smoke()
        return
    if args.mode == "editor-rebuild-test":
        if not WINDOWS:
            parser.error("editor-rebuild-test currently validates Windows RunUAT only")
        # Deliberately inherit the ordinary OS environment, not environment().
        editor(engine_root(args.engine_root), None, args.mode)
        return
    env, dotnet = environment()
    engine = engine_root(args.engine_root)
    if args.mode == "build":
        build(engine, dotnet, env, args.disable_plugin)
    elif args.mode == "package":
        package(engine, dotnet, env, args.disable_plugin)
    elif args.mode == "prototype-build":
        prototype_build(engine, env)
    else:
        editor(engine, env, args.mode)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
