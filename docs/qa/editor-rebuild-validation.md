# 普通 UE 编辑器启动与重建修复

日期：2026-10-28（America/New_York）。基线为 `33abfbc`，开始时工作区干净。环境为 Windows x64、UE 5.8.3、UnrealSharp `115e6753`、项目本地 .NET SDK 10.0.403。

## 原因与复现

用户直接打开工程后，编辑器内部 `RunUAT BuildUserSolution` 报 `Couldn't find .NET SDK version 10.x in C:\Program Files\dotnet\sdk`，退出码 1。此前验证使用的专用启动器提供了 SDK 环境，普通启动没有相同的准备步骤。

本机继承的 PATH 长度为 9577。只追加项目 SDK 仍失败，完整启动器环境经批处理调用还会报找不到 `where`。为同一个 RunUAT 命令的子进程去掉重复／失效目录并加入项目 SDK 后，命令成功，证明无需修改 C# 玩法或删除构建缓存。cmd.exe 对继承环境变量的 8191 字符限制与该现象一致，见 [Microsoft 说明](https://learn.microsoft.com/en-us/troubleshoot/windows-client/shell-experience/command-line-string-limitation)。

新回归命令 `python Tools/unrealsharp.py editor-rebuild-test` 在修复前直接启动普通环境的编辑器，退出码 3，未能进入测试；修复后同一入口通过。测试有意不调用启动器的 `environment()`，实际调用编辑器内的 RunUAT，不能用外部 dotnet 编译通过替代。

## 修改

- OFFAIR 项目模块改为 `PreDefault` 加载，在 Windows 编辑器中先准备 SDK 路径和 UAT 版本变量。
- Windows 编辑器与 Python 入口只在当前进程内整理 PATH，保留有效目录的顺序，不修改系统／用户环境配置或安装全局 SDK。
- SDK 缺失时记录 setup 提示。首次克隆仍需准备依赖并完成一次原生构建。
- 未改动 UnrealSharp 上游源码、游戏规则、输入、关卡或原型生成脚本。新的启动准备代码不在游戏构建中执行。

## 实际验证

| 检查 | 结果 |
| --- | --- |
| 原生与托管编译 | `python Tools/unrealsharp.py build --disable-plugin Fab` 通过；本机 Fab 规则问题仍沿用既有构建排除参数 |
| 普通启动与编辑器内部重建 | `editor-rebuild-test` 4 项检查通过，实际进程 PATH 长度 2548，RunUAT 返回 0，项目 C# 类已加载 |
| 蓝图编译 | 现有 7 个项目蓝图内存编译成功，没有重新生成或保存关卡资产 |
| 有画面普通启动 | 直接运行 UnrealEditor.exe 加载 OFFAIR.uproject，未使用 SDK 启动包装器；关卡成功打开 |
| 编辑器 C# 重编译 | 对探针做临时无行为变化的注释修改，观察到 Reloading C# 界面；日志记录编译、程序集卸载与重载成功，耗时 0.82 秒。恢复原字节后再次成功，耗时 0.26 秒 |
| Play 验证 | 通过编辑器快捷键进入 PIE，看到阶段 0、玩家与正常 HUD，日志出现 `OFFAIR_RUN_READY`；结束 PIE 后编辑器保持打开 |

结构化证据见 [编辑器内部重建](evidence/editor-rebuild-result.json)与[界面验证摘要](evidence/editor-rebuild-gui.json)。本机原始失败、探测与最终日志在被 Git 忽略的 `Saved/EditorRebuild/`。

本轮没有重建关卡几何／灯光，没有重复完整 44 项玩法或跨平台验收，没有重新打包。此次热重载检查仅覆盖无行为变化的注释修改及恢复，不代表验证了类型结构变更或游戏中热重载。
