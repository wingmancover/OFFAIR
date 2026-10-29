# UnrealSharp 接入

接入日期：2026-10-28。用户已选择引入 UnrealSharp，并明确 Mac 只考虑 Apple Silicon。

## 范围与依赖

- UE 保持 5.8；本机 Windows 安装为 5.8.3。
- UnrealSharp 子模块：`Plugins/UnrealSharp`，固定提交 `115e6753b2f8c830f084a3e453b7ef3b1230eb33`，保留上游 MIT 许可证。
- .NET SDK 固定为 `10.0.403`；下载地址与 SHA-512 在 `Tools/unrealsharp.lock.json`。安装到被忽略的 `Saved/Toolchains/`，不提交 SDK 或修改系统 PATH。
- 目标为 Windows x64 与 macOS arm64。Mac 需要实际 Apple Silicon 机器、匹配 UE 5.8 的 Xcode 和系统；本机不能完成 Mac 构建或运行验收。
- 工具入口要求 Python 3.12+。Windows 还需要 UE C++ 工具链；本机使用 VS 2022 的 MSVC 14.44 与 Windows SDK 10.0.22621.0。VS 2022 不支持 .NET 10 C# 项目；命令行构建与编辑器脚本迭代不依赖其 C# IDE 支持。

现有角色、武器、敌人、阶段状态、监控与 GM 继续使用原蓝图。`Source/OFFAIR` 注册项目原生模块，并提供限定在 PIE 世界中生效的测试 Actor 生成入口；`Script/OFFAIR/Offair.Managed.csproj` 是项目 C# 工程。`AOffairScriptProbe` 是独立互调样例，没有正式玩法职责。

探针只有实例内 `CallCount`，初始为 0，随 Actor／世界销毁，不跨死亡或 PIE 保留；没有计时器、输入绑定、静态 Actor 引用和跨循环状态。验证蓝图位于 `/Game/OFFAIR/Tests/BP_UnrealSharpProbe`，不会自动放进正式地图。

## 准备、构建与启动

从仓库根目录执行（macOS 可将 `python` 替换为 `python3`）：

```sh
python Tools/unrealsharp.py setup
python Tools/unrealsharp.py build
python Tools/unrealsharp.py editor
```

`setup` 初始化缺少的子模块并校验 SDK 下载。已有子模块若不是固定版本会报错，不自动覆盖本地修改。引擎目录可通过 `--engine-root` 或 `UE_ENGINE_ROOT` 指定；工具拒绝非 UE 5.8 引擎。

本机 Launcher 引擎的 Fab 插件声明 `FabToolset`，但已安装的 UE5Rules 中缺少对应构建规则，需要对原生编辑器构建显式排除：

```sh
python Tools/unrealsharp.py build --disable-plugin Fab
python Tools/unrealsharp.py package --disable-plugin Fab
```

此参数只影响该次原生编译，不改写 `.uproject` 中的 Fab 配置，不改变引擎安装。其他机器没有这个问题时无需添加。`build` 会生成 IDE／版本文件，编译原生插件与项目模块，再构建项目 C# 和程序集加载清单，不重新生成现有玩法蓝图。

固定上游在 Windows 从 PATH 中查找包含 `Program Files\dotnet\` 的目录，因此项目 SDK 使用 `Saved/Toolchains/Program Files/dotnet/` 后缀并由工具临时加入子进程 PATH。macOS 使用 `Saved/Toolchains/dotnet/`；若机器已经存在 `/usr/local/share/dotnet`，上游编辑器会优先使用它，工具检查其 .NET 10.0.5+ 运行时，版本不满足时明确报错。启动编辑器使用上述 `editor` 命令，以带入依赖环境。

固定上游还使用 `UE5Rules.csproj` 推断 Automation/UHT 的 .NET 目标。部分 Launcher 安装没有这个文件；工具在验证引擎版本后，为子进程补充 `UE_5_8_OR_LATER` 版本常量，并通过 `UE_USE_SYSTEM_DOTNET=1` 保持编辑器内部启动 UAT 时使用同一份本地 SDK。没有修改插件源代码。

`Script/OFFAIR.RuntimeGlue/` 是插件按当前项目资源自动生成的绑定，整体忽略；作者代码不要放入该目录。构建、启动编辑器会自动生成和更新这些文件。

## 验证与打包

```sh
python Tools/unrealsharp.py smoke
python Tools/unrealsharp.py test
python Tools/unrealsharp.py package
python Tools/unrealsharp.py package-smoke
```

- `smoke`：通过 UE 图表 API 生成／编译独立蓝图子类，调用 C# 并读取反射属性，测试死亡重载后的新实例及第二次 PIE。只保存专用测试资产。
- `test`：运行原有 `validate_prototype.py`，覆盖正常通关、阶段推进、监控与 GM 回归。
- `package`：在当前平台构建 Development 包，然后运行 UnrealSharp 的托管打包步骤，输出到 `Saved/Packages/`。Windows 为 x64，Mac 为 arm64。此命令不发布或上传产物。
- `package-smoke`：清除子进程中的项目 SDK 环境，在编辑器外以 NullRHI 启动 Development 包，检查自包含运行时、作者程序集加载和原型初始化。它不验证画面、性能或完整键鼠通关。

本机 Windows 包位于 `Saved/Packages/Win64/OFFAIR.exe`；应保留整个 `Win64` 目录，不能只复制单个 exe。托管程序集和 .NET 运行时位于其中的 `OFFAIR/Binaries/Managed/net10.0/`。

旧 `Tools/Run-Unreal.ps1 -Mode Build` 是重建玩法资产的命令，不能代替 C++/.NET 编译。普通 C# 修改不需要重建关卡。后续将玩法函数迁入 C# 时必须同步对应蓝图生成器，避免生成器写回另一套实现。

实际验证结果见 [UnrealSharp 接入验证](../qa/unrealsharp-validation.md)。Mac 的构建、Metal 画面、性能以及签名分发尚需在 Mac 上验证；最低 M 系列型号与画质目标未确定。

## 上游依据

- [源码与支持平台](https://github.com/UnrealSharp/UnrealSharp)
- [安装](https://www.unrealsharp.com/getting-started-and-fundamentals/quickstart)
- [C# 类型与蓝图](https://www.unrealsharp.com/getting-started-and-fundamentals/your-first-script)
- [打包流程](https://www.unrealsharp.com/getting-started-and-fundamentals/packaging)
