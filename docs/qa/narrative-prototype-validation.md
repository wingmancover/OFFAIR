# 三阶段叙事原型验证

用户后续试玩确认三阶段流程并自行提交为 `158c979`，随后要求仅将第二次复活对白延长两秒。已定向修改、编译并保存 `BP_RunDirector.CommitRun`：S1 仍为三秒，S2 为五秒，同时同步作者脚本与验收计时。独立 PIE 定向检查通过：初始化分别为 3.0/5.0 秒，S2 四秒时仍可见，5.5 秒后文本与计时均清空，见[时长结果](evidence/thought-duration-result.json)。该测试通过 GM 进入目标阶段，仅验证对白计时，没有重跑下文 44 项完整回归。地图文件修改前后 SHA256 相同，未覆盖用户调整的 Anchor 位置；未暂存、提交或推送。下文保留首次三阶段实现的历史记录。

2026-10-19，Windows / Unreal Engine 5.8.3 / 单人 PIE。基线为用户已提交的 `b1ee8e1`。蓝图与地图已保存，等待用户试玩；没有暂存、提交或推送。规则见[三阶段设计](../design/narrative-prototype.md)，操作见[游玩说明](../prototype-play-guide.md)。

## 变更与构建

- `BP_RunDirector`：三阶段基线、纸条三秒输入锁与伤害死亡、盒子陷阱、独立阶段生命、心理对白计时，以及 GM 和重置清理。
- `BP_PrototypeHUD`：中央系统提示与底部浅青色心理对白，使用深色底板。
- `Lvl_Prototype`：移除 StageGate、核心底座和过时标识；核心改为地面红色薄纸片；增加金色盒子与独立陷阱敌人出生点。保留枪、权限卡、直接黑入与出口逻辑。
- 作者脚本同步更新；使用 `build_prototype.py --director-only --include-hud` 定向生成、编译、保存两个受影响蓝图，并增量迁移地图，没有重建无关模板资产。产物与 SHA256 见[清单](evidence/narrative-artifact-manifest.json)。

另起编辑器进程载入已保存资产，完成导航构建和 PIE 验证。出生、原隔墙后方、盒子、陷阱敌人、常规守卫、监控通道共六处导航投影成功，见[导航结果](evidence/narrative-navigation.json)。本轮没有执行打包测试或全量资产重建。

## 自动化结果

最终 `validate_prototype.py` 与 `runtime_regressions.py` 共 **44 项通过，60.50 秒**，见[原始结果](evidence/narrative-runtime-result.json)。最终构建与测试日志未检出 `Error:`、`Accessed None`、`Blueprint Runtime Error` 或 Python traceback。

| 范围 | 实测行为 |
| --- | --- |
| S0 | 可穿过原隔墙位置探索，但不能提前完成；拾条前死亡重试 S0；正常交互拾条后显示系统提示，三秒后真实死亡复活进入 S1；重复操作不能推进两次 |
| S1 | 100 生命、无初始敌人和枪；盒子交互生成一名立即攻击的敌人并锁定 S2；重复交互不重复生成；真实模板子弹命中记录为 100、75、50、25，下一次命中死亡后进入 S2 |
| S2 | 恢复 500 生命和枪械；守卫拿枪前待机、拾枪后行动；正常模板武器击杀、掉卡、拾卡、直接黑入、转向退出与正常通关通过 |
| 重置与异常 | 开盒前死亡重试 S1；GM 打断陷阱清除敌人及待生效阶段；旧倒计时不能杀死新一轮；对白到期清理；十轮重置未发现状态或 Actor 泄漏；初始化失败恢复通过 |
| 监控与 GM 回归 | 权限、目标模型瞄准、15 米距离、遮挡、俯仰方向、死亡和设备失效退出、警报锁路、GM 边界及移除不计击杀等通过 |

正常路线没有用 GM 跳阶段或脚本伤害代替陷阱死亡；测试驱动通过正常交互函数和模板投射物完成主线。GM、强制位置和异常状态注入属于隔离测试夹具，不等同于真实键鼠操作。

## 实际按键与画面

图形编辑器中另做原生键盘输入验证：夹具只负责摆放角色和对准目标，纸条、盒子由 Windows 键盘 E 事件触发。真实陷阱敌人完成射击致死，第二次复活恢复 500 生命；两段对白均显示并在三秒后消失，见[按键流程结果](evidence/narrative-input-result.json)。

另一次纸条实测在中央提示期间按住 W 与 R：记录的平面位移为 **0.0 cm**，R 没有跳过锁定；仍由三秒倒计时结束后的死亡进入 S1，见[锁定检查](evidence/narrative-lock-input-result.json)。没有逐一穷举所有物理按键；其他锁定入口由自动化重复交互和 GM 用例覆盖。

已查看 Unreal 原生 1280×720 截图，确认提示位置、颜色、深色底板和两行对白显示：

- [红色纸片](evidence/narrative-note.png)
- [中央系统提示](evidence/narrative-system-error.png)
- [第一次心理对白](evidence/narrative-first-thought.png)
- [金色盒子](evidence/narrative-gold-box.png)
- [第二次心理对白](evidence/narrative-second-thought.png)

纸片与盒子为灰盒形状；场景仍沿用原有亮光，因此地面纸片与原有世界文字的最终可读性仍待用户试玩。整体灯光、旧 HUD 可读性与翻越按用户要求留给后续迭代。本轮结束 PIE，保留编辑器供用户从 S0 重新试玩；[最终编辑器状态](evidence/narrative-editor-final.json)确认当前地图为 `Lvl_Prototype`，无未保存地图或内容包，MCP 工具列表连接也已恢复。
