# UnrealSharp 接入验证

日期：2026-10-28（America/New_York）。基线：`d1b37ce`。

环境：Windows x64，UE 5.8.3，MSVC 14.44，Windows SDK 10.0.22621.0，项目本地 .NET SDK 10.0.403。UnrealSharp 固定为 `115e6753b2f8c830f084a3e453b7ef3b1230eb33`，没有修改上游源码。

## 与远程三阶段原型合并后的复核

用户要求提交推送时，远程 `main` 已前进到 `2522539`。将本地 UnrealSharp 提交 `2f901de` 与该远程版本合并，保留三阶段叙事、直接摄像机黑入、空格翻越、关卡布局、打包配置和编辑器连接配置；五处冲突仅为文档与忽略规则，按双方意图合并。

- `python Tools/unrealsharp.py build --disable-plugin Fab` 通过，新的插件组合可与 UnrealSharp 一起构建。
- `python Tools/unrealsharp.py test` 通过 **44 项**当前三阶段玩法回归，测试耗时 61.73 秒，不含编辑器启动。
- `python Tools/unrealsharp.py smoke` 通过 **5 项**互调／生命周期检查，测试耗时 1.33 秒。测试重新生成的专用探针蓝图一并保存。
- 两次测试日志未发现 `Error:`、`Fatal error`、`Accessed None` 或 `Traceback`；远程 `Content/OFFAIR/Core`、`Levels`、`UI` 与 `Input` 资产未被改写。
- 本次合并未重新打包，也未重复翻越真实键鼠检查；下文 Windows 打包记录和当前 `Saved/Packages/Win64` 产物对应初次接入时的两阶段基线，不能作为最新三阶段包的验证结果。最新源代码打包仍使用接入说明中的命令。

结果：[44 项三阶段回归](evidence/unrealsharp-merge-runtime.json)、[5 项接入检查](evidence/unrealsharp-merge-smoke.json)。

## 初次接入已通过

| 验收 | 命令与实际结果 |
| --- | --- |
| S-01 原生与托管构建 | `python Tools/unrealsharp.py build --disable-plugin Fab`；插件、项目原生模块、C# 引擎绑定、作者工程和程序集加载清单成功生成 |
| S-02 蓝图互调 | `python Tools/unrealsharp.py smoke`；加载 C# UClass，保存并编译 `BP_UnrealSharpProbe`，由蓝图调用 C# 得到 41 → 42、-1 → 0，反射属性计数为 1、2 |
| S-03 生命周期 | 同一次 smoke 中调用正常伤害死亡入口重载地图，旧探针消失，新实例计数为 0；第二次 PIE 同样从 0 开始。共 5 项检查通过 |
| S-04 玩法回归 | `Tools/Run-Unreal.ps1 -Mode Test`；原有 25 项检查通过，测试阶段耗时 31.30 秒（不含编辑器启动） |
| S-05 Windows 打包与启动 | `python Tools/unrealsharp.py package --disable-plugin Fab` 和 `python Tools/unrealsharp.py package-smoke`；Development 包生成成功，清除项目 SDK 环境后，包内 .NET、自有程序集、原型初始化及无运行错误 4 项检查通过 |

S-04 包含不开 GM 的正常拾取、死亡延迟推进、模板枪械击杀、权限卡、监控转向／退出及抵达终点，也包含重复事件、重建失败恢复、设备失效、监控中死亡与连续混合重置。使用原测试驱动，未改写玩法断言来适应插件。

原始结构化结果：[5 项互调与生命周期检查](evidence/unrealsharp-smoke.json)、[25 项玩法回归](evidence/unrealsharp-runtime-regressions.json)、[打包程序启动检查](evidence/unrealsharp-package-smoke.json)、[依赖与产物摘要](evidence/unrealsharp-integration.json)。本机完整日志位于被忽略的 `Saved/UnrealSharpTests/`、`Saved/PrototypeTests/`、`Saved/UnrealSharpPackageTests/`、`Saved/UnrealSharp-build.log` 和 `Saved/UnrealSharp-package.log`。

最终 smoke 与玩法回归日志中未发现 `Error:`、`Accessed None`、`LogBlueprint: Error` 或 `Traceback`。上游分析器存在 Roslyn 规则发布跟踪警告，Game 绑定发布存在生成代码的 nullable 警告；构建退出码均为 0，未改写上游源码来消除这些警告。

## 构建兼容处理

- 本机 Fab 的描述文件包含 `FabToolset`，但安装的 UE5Rules 缺少对应规则。通过构建参数排除 Fab；没有禁用工程的 Fab 配置或修改引擎安装。
- Launcher 安装未生成上游用于版本判断的 UE5Rules.csproj。入口在核对 UE 5.8 后传递版本常量，使 UHT 扩展使用 .NET 10。
- 编辑器内部 UAT 使用同一份 SDK；避免其切换到本机旧 .NET SDK。Windows 项目本地 SDK 路径后缀兼容固定插件的路径查找规则。
- Python 没有公开对应的运行时 SpawnActor API；新增一项仅允许 PIE 世界的原生测试桥接。正式关卡未引用此入口。

## 验证边界

Windows 使用 Development 配置、NullRHI 启动检查；这证明包内运行时与程序集能在本机独立加载，不代表验证了画面、性能、完整打包通关或一台未装开发工具的机器。macOS arm64 的构建、打包、运行、画面、性能、签名与分发均未执行；本机没有可用 Mac 执行环境。

本轮未迁移阶段、监控、输入、敌人与武器逻辑；没有重新生成现有玩法资产，旧资产 Build 路径只保留行为并完成静态审阅，未重新执行整图生成。未重复真实键鼠验收，没有验证代码／类型结构的热重载、Shipping 配置或没有开发工具的独立机器。旧原型验证记录保留为历史基线。
