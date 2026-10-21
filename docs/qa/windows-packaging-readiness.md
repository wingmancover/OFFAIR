# Windows 作业打包前复核

2026-10-21，Git 基线 `647337c`（Updated Vaulting system），开始时工作区干净。用户选择由自己操作编辑器界面、代理逐步指导与检查；尚未生成或验证 Windows 独立运行包。

## 当前一致的进度

- S0 红纸条按 E，系统三秒锁定后死亡进入 S1；S1 开金盒后陷阱敌人攻击致死进入 S2；S2 恢复 500 生命，E 拾枪后守卫启动、击杀掉卡、取得权限后直接黑入摄像头并通关。
- 心理对白依次三秒、五秒；灯光与提示对比度已由用户试玩确认。空格优先翻越、其他情况跳跃，V 已移除。用户确认最终版本已保存上传。
- 最新历史证据为 44 项阶段／监控回归、13 项翻越与长按检查、2 项空格回退／复活输入检查。它们是编辑器 PIE 结果，不能代替独立包测试。
- 已清点 574 个受版本管理文件：468 个 uasset、3 张地图、23 份 Markdown、35 份 JSON、10 个 Python 脚本及其他配置／证据；JSON、Python 语法与文档本地链接检查通过。二进制资产以编辑器与引用配置检查，不按文本解析。复核时同步了仍写 V、翻越延后或两段对白均三秒的旧说明，未修改玩法资产。

## 实际环境与设置

| 项目 | 检查结果 |
| --- | --- |
| 当前编辑器 | `Y:/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe`，安装版本 5.8.4；历史验证记录为 5.8.3，未由代理升级 |
| Windows SDK | `Y:/Windows Kits/10` 下有 10.0.20348.0、10.0.22621.0、10.0.26100.0；尚未执行打包或 Turnkey 验证 |
| 当前打开／默认游戏地图 | `/Game/OFFAIR/Levels/Lvl_Prototype` |
| 默认 GameMode／GameInstance | `BP_OFFAIRGameMode`／`BP_OFFAIRSession` |
| 实际编辑器打包配置 | 用户已在界面设置并写入 `DefaultGame.ini`：Development；Pak、Io Store、Zen cooked output、压缩、Include Prerequisites 开启；Include Debug Files 关闭；Cook All 关闭；Maps to Cook 仅含 `/Game/OFFAIR/Levels/Lvl_Prototype`；截图与文件一致 |
| 画质默认值 | 新增 `Config/DefaultGameUserSettings.ini`：按用户确认，首次启动默认无边框全屏、显示器原生分辨率（`bUseDesktopResolution=True`，分辨率字段为 0，启动时检测）、Epic（各画质组 3）、100% 渲染比例，关闭动态分辨率；配置格式与本机 UE 5.8.4 源码字段已核对，尚未在独立包验证 |
| 运行状态 | MCP 已连接，PIE 未运行 |

打包选项由用户在编辑器修改；代理新增首次启动画质配置并同步文档，未修改玩法资产，没有暂存、提交、推送或上传。作业首包使用 Development 便于诊断并演示现有 GM，不把 Shipping 自动等同于关闭自制 GM。明确仅 Cook `Lvl_Prototype` 及其依赖，运行画质须与编辑器视口设置分开验证。

`DefaultGameUserSettings.ini` 是首次启动默认值，已有用户配置可以覆盖它；后续运行包检查时需核对实际生效值，不删除用户已有配置。100% 表示按输出分辨率渲染，不代表所有硬件均能流畅运行，也不能代替对抗锯齿、运动中观感和 UI 的实际观察。Zen cooked output 是烘焙数据存储选项，其开启本身不能推断成品依赖外部 Zen 服务；最终须从完整暂存目录验证离线启动。

## 后续通过条件

在编辑器完成打包配置及画质默认值后，生成 Windows 包、脱离编辑器启动 exe，以真实键鼠复测主线、空格、GM 与重置，检查导航、权限卡、监控转向退出和终点；再检查运行分辨率、渲染比例、文字及灯光表现。完成后压缩整个打包目录，不能只交 exe；另一台 Windows 机器复测兼容性和性能。

不要用 `Tools/Run-Unreal.ps1 -Mode Build` 代替打包：该命令会重新生成蓝图和地图，可能覆盖用户已手调的布局。Windows 打包使用编辑器 Platforms 菜单或 UAT，不需要重建原型资产。

步骤依据：[Epic 打包说明](https://dev.epicgames.com/documentation/unreal-engine/packaging-your-project)、[分辨率与可伸缩画质说明](https://dev.epicgames.com/documentation/unreal-engine/scalability-reference-for-unreal-engine)。
