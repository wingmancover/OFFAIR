# 双房间 Windows 试玩包（2026-11-16）

用户授权先打包进行试玩，关键音效已由用户在此前试玩中确认；翻越暂缓。本次不改玩法、地图、音效、标题或渲染配置，不暂存、提交或推送 Git。

## 产物与构建

- 基于用户已提交的 `bd55968` 游戏内容，地图为 `/Game/OFFAIR/Levels/Lvl_TwoRoom_Blockout`。
- UE 5.8.4，Windows x64 Development，使用项目现有 Pak／IoStore 设置。
- 文件夹：`Saved/Packages/Win64/`，运行其中顶层 `OFFAIR.exe`。
- 分发 ZIP：`Saved/Packages/OFFAIR-Windows-2026-11-16.zip`；完整解压，保留所有子目录。包内有 `READ-ME-FIRST.txt`，不包含谜题答案。
- .NET 运行时和项目程序集已随包发布；不需要 Unreal 编辑器或独立安装 .NET。Visual C++ x64 安装器位于包内 `Engine/Extras/Redist/en-us/vc_redist.x64.exe`。
- 默认配置保持无边框全屏、桌面原生分辨率、100% 渲染比例、关闭动态分辨率；已有本地用户设置可能覆盖默认值。

发现并修正 `Tools/unrealsharp.py package` 写死旧地图的参数，改为使用项目地图列表；加入运行依赖和排除原生调试符号参数。先完成原生编译、Cook、Stage、Archive 和托管发布，再复用本次 Cook 结果以最终参数重新 Stage／Archive／托管发布。未重建玩法资产或修改插件版本。

## 实际验证

1. 编辑器／游戏原生编译、资源 Cook、最终归档和 UnrealSharp 托管发布成功，返回码 0。
2. `python Tools/unrealsharp.py package-smoke` 成功：独立进程移除项目 SDK 环境，确认自包含运行时、`Offair.Managed.dll` 加载、新地图进入游玩，以及启动日志无运行错误。
3. 实际包内 EXE 以 D3D12 离屏渲染启动，使用独立测试 UserDir，1600×900 测试视口；截图确认新教学房、两把展示枪、红信、巨蛋、目标与主持人文字显示。测试正常退出，返回码 0，无 Error／Fatal／Unhandled exception。
4. 渲染退出清理期间有一条 `Unable to find RecastNavMesh instance while trying to create UCrowdManager instance` 警告。不能据此确认战斗导航正常或异常；本轮未触发战斗，包内敌人追击需人工补测。
5. ZIP 内 280 个文件逐项 CRC 校验通过。文件夹 887,571,381 字节，ZIP 515,187,021 字节；ZIP SHA-256：`af5946ab71c3ff37e1db390d73cccae3284db11ef04ce84387574cc382eb8509`。

原始日志、截图和分发校验记录分别位于 `Saved/PlaytestPackage-2026-11-16/`、`Saved/UnrealSharpPackageTests/`，均为本地产物，不提交。离屏检查使用 `-nosound`；不把此前编辑器音效确认记成打包音效验证。

## 本轮尚未验证

- 不开 GM 的完整键鼠通关：首次死亡、两枪分支、敌人战斗和掉卡、C1、C2、射击提交、错误死亡、B 保存、观景与三秒标题。
- 包内声音、多轮重试、B 后死亡保留、完整退出重启后的新会话。
- 实际桌面全屏、不同显示器／分辨率、目标电脑性能与干净 Windows 机器运行依赖。
- 截图中出生操作提示与字幕底部接近，试玩时可留意遮挡；本次不修改 UI。
- macOS 构建与运行；本产物只适用于 Windows x64。

完整功能以包内人工试玩结果为准，启动及截图检查不等于全流程回归通过。
