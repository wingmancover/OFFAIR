# 双房间第 2 步验证记录

2026-11-08，Windows x64，Unreal Engine 5.8.4，UnrealSharp 固定依赖未更新。本轮工作保存但未暂存、提交、推送或打包。上轮布局尚未提交的文件保留；旧 `Lvl_Prototype`、模板蓝图、工程默认地图和打包配置未改动。

## 实际结果

| 验证 | 结果与证据 |
| --- | --- |
| C# 构建 | `Tools/unrealsharp.py managed-build --engine-root Y:/UE_5.8`，UAT 成功退出 0 |
| 区域集成 | 69 项通过；[原始检查](evidence/region-loop-validation-result.json) |
| 导航与角色行走 | 35 项通过；[原始检查](evidence/region-loop-navigation-result.json) |
| 受影响蓝图 | `BP_RegionLoopDirector`、`BP_RegionHUD`、`BP_RegionCharacter`、`BP_RegionGameMode` 编译通过 |
| 地图检查 | 最终捕获运行中 MapCheck：0 errors / 0 warnings |
| 实际游戏画面 | 独立隐藏编辑器 RenderOffscreen PIE，1600×900；检查出生点、信件提示、普通玩家／C2 视图、GM、B 保存、穹顶 |

区域检查通过真实角色、摄像机视线和遮挡检测调用交互入口；覆盖首次三秒等待、重入拒绝、普通重试、可选再次读信、未保存旗标／模型／门／摄像机变换恢复、临时生成物销毁、旧尝试事件与迟到生成隔离、初始化缺引用失败、真实 AnyDamage 事件、远程死亡清理、B 条件拒绝、B 幂等保存、存档后进度及完成区域保留、新 PIE 清空。

导航实际重建并保存；16 个点成功投影到可行走面，并通过 CharacterMovement 连续移动经过 14 个路径点。D2 关闭时角色被挡在门前；完成首次记忆、明确使用 GM 测试条件开门后，角色实际移动穿门到 B。没有用 Recast Actor 单独存在来替代导航验证。

最终游戏画面对照确认：从 C2 可看见高处柜内答案；普通角色即使被测试脚本移至 C2 的观察位置并朝同方向看，仍看不到背板和图案。两视角 FOV 不同，因此不是逐像素对照。没有依赖“玩家站得不够高”作为唯一遮挡条件。

- [C2 可见图案](evidence/region-pattern-camera.png)
- [普通角色同位置不可见](evidence/region-pattern-player.png)
- [B 已保存界面](evidence/region-checkpoint-b.png)

## 验证方法与限制

- 自动交互通过 `HandleRegionInput` 调用，但保留真实距离／视角／遮挡判定；伤害验证还经过角色的实际 `ReceiveAnyDamage` 蓝图桥。**未发送 OS 键鼠，也未把函数调用标记为物理按键通过**。需用户试玩确认 E／R／F1／数字键、跳跃锁定与输入手感。
- 真实运行输入由玩家控制器的按键状态读取；检查过工程已有 F1 默认 wireframe 解绑配置，未增加新全局输入设置。
- 音效已导入、引用并验证播放调用次数；后台以 `-nosound` 运行，未验证扬声器听感。音量／音色由用户最后试听。
- 第 2 步只有进度旗标与已登记对象状态；不存在实际敌人、射击谜题生产者。后续必须在这些功能接入后补真实重置、卡片和枪械恢复、计时器隔离、谜题失败死亡等测试。
- GM 的测试条件不能替代正常战斗与解谜验收；C2 预览没有正式黑入输入或构图交互。
- 未测试 macOS、打包、退出进程后的读档；本设计无磁盘存档。
- 后台辅助编辑器日志有 `127.0.0.1:8000` 已被主编辑器占用的 MCP 监听错误；没有用于测试的连接依赖此端口，不能宣称整个日志零错误。最终测试没有区域脚本异常或蓝图运行错误。初次作者脚本／测试接口适配失败已修复，以上结果来自最终成功运行。

## 可复现入口

作者脚本 `Tools/unreal/build_region_loop.py` 以命令行编辑器 Python commandlet 执行；不要让主编辑器同时持有待写的地图。随后运行 `Tools/unreal/validate_region_navigation.py`（隐藏编辑器，`-NullRHI -ExecutePythonScript`）重建导航并保存。

`Tools/unreal/validate_region_loop.py` 使用独立 PIE 验证状态与交互；`Tools/unreal/capture_region_loop.py` 使用 `-RenderOffscreen` 生成实际游戏截图。完整日志、音频源和临时截图在被忽略的 `Saved/RegionLoop/`，本页引用的检查与三张图是本次保留的验收证据。

用户试玩流程见[区域循环说明](../design/region-loop-checkpoint.md)。本轮保留了 `Saved/RegionLoop/step1-backup.umap` 作为本机变更前备份；它不入库，不能用普通文件操作替换已加载地图来恢复。
