# UnrealSharp 接入

接入日期：2026-10-28。用户已选择引入 UnrealSharp，并明确 Mac 只考虑 Apple Silicon。

## 范围与依赖

- UE 保持 5.8；第 2 步本机 Windows 实际验证为 5.8.4（早期接入记录为 5.8.3）。
- UnrealSharp 子模块：`Plugins/UnrealSharp`，固定提交 `115e6753b2f8c830f084a3e453b7ef3b1230eb33`，保留上游 MIT 许可证。
- .NET SDK 固定为 `10.0.403`；下载地址与 SHA-512 在 `Tools/unrealsharp.lock.json`。安装到被忽略的 `Saved/Toolchains/`，不提交 SDK 或修改系统 PATH。
- 目标为 Windows x64 与 macOS arm64。Mac 需要实际 Apple Silicon 机器、匹配 UE 5.8 的 Xcode 和系统；本机不能完成 Mac 构建或运行验收。
- 工具入口要求 Python 3.12+。Windows 还需要 UE C++ 工具链；本机使用 VS 2022 的 MSVC 14.44 与 Windows SDK 10.0.22621.0。VS 2022 不支持 .NET 10 C# 项目；命令行构建与编辑器脚本迭代不依赖其 C# IDE 支持。

现有角色、武器、敌人、阶段状态、监控与 GM 继续使用原蓝图。`Source/OFFAIR` 注册项目原生模块，在 Windows 编辑器启动时准备进程内 SDK 环境，并提供限定在 PIE 世界中生效的测试 Actor 生成入口；`Script/OFFAIR/Offair.Managed.csproj` 是项目 C# 工程。`AOffairScriptProbe` 是独立互调样例，没有正式玩法职责。

2026-11-08 用户授权按效率选择实现语言。新 `Lvl_TwoRoom_Blockout` 的第 2 步循环／会话存档与小型 HUD 分别由 `RegionLoopDirector.cs`、`RegionHUD.cs` 实现；蓝图继承 FirstPerson 角色并连接伤害事件。旧地图未迁移，插件固定版本未改变。状态生命周期与验证见[区域循环](../design/region-loop-checkpoint.md)。

新增 `python Tools/unrealsharp.py managed-build --engine-root Y:/UE_5.8`，使用项目既有 SDK 和 UAT `BuildUserSolution` 只编译托管代码，适用于完成初次原生构建后的 C# 迭代；本轮已实际成功执行。首次克隆／依赖改变仍需 setup/build，不能用 managed-build 替代原生编译。C# 与 Python 作者源码入库，`Binaries/Managed` 等生成结果不提交。

探针只有实例内 `CallCount`，初始为 0，随 Actor／世界销毁，不跨死亡或 PIE 保留；没有计时器、输入绑定、静态 Actor 引用和跨循环状态。验证蓝图位于 `/Game/OFFAIR/Tests/BP_UnrealSharpProbe`，不会自动放进正式地图。

## 准备、构建与启动

从仓库根目录执行（macOS 可将 `python` 替换为 `python3`）：

```sh
python Tools/unrealsharp.py setup
python Tools/unrealsharp.py build
python Tools/unrealsharp.py editor
```

`setup` 初始化缺少的子模块并校验 SDK 下载。已有子模块若不是固定版本会报错，不自动覆盖本地修改。引擎目录可通过 `--engine-root` 或 `UE_ENGINE_ROOT` 指定；工具拒绝非 UE 5.8 引擎。

Windows 完成首次 setup/build 后，也可直接双击 `OFFAIR.uproject`。OFFAIR 模块在 `PreDefault` 加载阶段配置当前编辑器进程，早于 UnrealSharp 的 SDK 查找与 UAT 调用。它选择项目本地 SDK，保留有效 PATH 目录的顺序并去重，剔除已不存在的目录；不会修改注册表、用户或系统环境变量。删除 `Saved/Toolchains` 或首次克隆后仍需先运行 setup/build，未编译的原生模块无法在启动前替代构建工具链准备。

本机 Launcher 引擎的 Fab 插件声明 `FabToolset`，但已安装的 UE5Rules 中缺少对应构建规则，需要对原生编辑器构建显式排除：

```sh
python Tools/unrealsharp.py build --disable-plugin Fab
python Tools/unrealsharp.py package --disable-plugin Fab
```

此参数只影响该次原生编译，不改写 `.uproject` 中的 Fab 配置，不改变引擎安装。其他机器没有这个问题时无需添加。`build` 会生成 IDE／版本文件，编译原生插件与项目模块，再构建项目 C# 和程序集加载清单，不重新生成现有玩法蓝图。

固定上游在 Windows 从 PATH 中查找包含 `Program Files\dotnet\` 的目录，因此项目 SDK 使用 `Saved/Toolchains/Program Files/dotnet/` 后缀，由命令行入口和 Windows 编辑器模块配置进程 PATH。macOS 使用 `Saved/Toolchains/dotnet/`；若机器已经存在 `/usr/local/share/dotnet`，上游编辑器会优先使用它，工具检查其 .NET 10.0.5+ 运行时，版本不满足时明确报错。Mac 继续使用上述 `editor` 命令，以带入依赖环境，普通启动路径未在 Mac 实测。

固定上游还使用 `UE5Rules.csproj` 推断 Automation/UHT 的 .NET 目标。部分 Launcher 安装没有这个文件；工具在验证引擎版本后，为子进程补充 `UE_5_8_OR_LATER` 版本常量，并通过 `UE_USE_SYSTEM_DOTNET=1` 保持编辑器内部启动 UAT 时使用同一份本地 SDK。没有修改插件源代码。

`Script/OFFAIR.RuntimeGlue/` 是插件按当前项目资源自动生成的绑定，整体忽略；作者代码不要放入该目录。构建、启动编辑器会自动生成和更新这些文件。

## 验证与打包

```sh
python Tools/unrealsharp.py smoke
python Tools/unrealsharp.py test
python Tools/unrealsharp.py package
python Tools/unrealsharp.py package-smoke
python Tools/unrealsharp.py editor-rebuild-test
```

- `smoke`：通过 UE 图表 API 生成／编译独立蓝图子类，调用 C# 并读取反射属性，测试死亡重载后的新实例及第二次 PIE。只保存专用测试资产。
- `test`：运行原有 `validate_prototype.py`，覆盖正常通关、阶段推进、监控与 GM 回归。
- `package`：在当前平台构建 Development 包，然后运行 UnrealSharp 的托管打包步骤，输出到 `Saved/Packages/`。Windows 为 x64，Mac 为 arm64。此命令不发布或上传产物。
- `package-smoke`：清除子进程中的项目 SDK 环境，在编辑器外以 NullRHI 启动 Development 包，检查自包含运行时、作者程序集加载和原型初始化。它不验证画面、性能或完整键鼠通关。
- `editor-rebuild-test`：Windows 专用，故意不注入启动器 SDK 环境，启动普通编辑器并在其中实际执行 RunUAT 重建、加载 C# 类和内存编译 7 个项目蓝图，防止“命令行通过但普通编辑器打不开／重建失败”的回归。详情见[普通编辑器重建修复](../qa/editor-rebuild-validation.md)。

本机 Windows 包位于 `Saved/Packages/Win64/OFFAIR.exe`；应保留整个 `Win64` 目录，不能只复制单个 exe。托管程序集和 .NET 运行时位于其中的 `OFFAIR/Binaries/Managed/net10.0/`。

旧 `Tools/Run-Unreal.ps1 -Mode Build` 是重建玩法资产的命令，不能代替 C++/.NET 编译。普通 C# 修改不需要重建关卡。后续将玩法函数迁入 C# 时必须同步对应蓝图生成器，避免生成器写回另一套实现。

实际验证结果见 [UnrealSharp 接入验证](../qa/unrealsharp-validation.md)。Mac 的构建、Metal 画面、性能以及签名分发尚需在 Mac 上验证；最低 M 系列型号与画质目标未确定。

## 上游依据

- [源码与支持平台](https://github.com/UnrealSharp/UnrealSharp)
- [安装](https://www.unrealsharp.com/getting-started-and-fundamentals/quickstart)
- [C# 类型与蓝图](https://www.unrealsharp.com/getting-started-and-fundamentals/your-first-script)
- [打包流程](https://www.unrealsharp.com/getting-started-and-fundamentals/packaging)

## 新双房间第 3 步

`RegionLoopDirector.cs` 管理区域循环和教学交互，蓝图适配复用 Shooter 角色、守卫、手枪和子弹，`RegionHUD.cs` 使用运行时字体。先 `managed-build`，再按需运行 `Tools/unreal/build_region_tutorial.py` 增量作者脚本；后台 PIE 入口为 `validate_region_tutorial.py`，画面检查用 `capture_region_tutorial.py`。不要把旧原型 `test` 的结果当成新地图验证。详见[当前记录](../qa/region-tutorial-validation.md)。

## 双房间第 4 步

谜题仍由同一 `RegionLoopDirector.cs` 管理，子弹注册时绑定原生碰撞通知，不修改共享模板蓝图。增量作者入口为 `Tools/unreal/build_region_puzzle.py`，正常流程回归为 `Tools/unreal/validate_region_puzzle.py`；后者需渲染离屏截图。当前源生成器要求新增反射成员与带 UClass 的声明在同一文件，不能把 UProperty 随意拆入无 UClass 标记的 partial 文件。作者脚本只在内存编译既有导演／HUD 蓝图，地图保存新引用；不为未变更的图表额外重存资产。
