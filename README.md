# OFFAIR

OFFAIR 是处于原型阶段的毕业设计游戏项目：以第一人称探索、围绕阶段循环设计的关卡解谜为主，辅以少量 FPS 战斗和监控摄像机黑入。

玩家未满足当前阶段的关键条件时，死亡会让世界回到该阶段的初始状态；满足条件后，下一次死亡复活才会从后续阶段的初始状态开始。监控黑入允许玩家切换到设备视角并调整朝向，为自己的行动创造机会。

## 当前迭代范围

当前目标是完整可玩的原型：正常游戏交互与 GM 配套实现。玩家应能通过实际拾取、短战斗、阶段循环和监控黑入走通关卡；GM 提供点击死亡、前后阶段切换、增减敌人和一键接入监控，帮助调试同一套系统。此前“只做 GM、暂缓实际交互”的范围已取消。

当前已接入三阶段叙事灰盒（纸条重置、盒子陷阱、战斗与监控）、关键物品、模板 FPS 战斗、权限卡、监控黑入、告警与终点，以及配套 GM。运行时仍为纯蓝图，原模板资产保持不变。详细控制与正常通关路线见[游玩说明](docs/prototype-play-guide.md)，验证结果见[本轮测试记录](docs/qa/prototype-implementation-validation.md)。

## 当前工程

- 引擎关联版本：`OFFAIR.uproject` 中的 `5.8`。
- 当前仓库以蓝图资产为主，未发现 `Source/` 或项目 C++ 模块声明。
- 默认启动地图：`/Game/OFFAIR/Levels/Lvl_Prototype`。
- 项目专用玩家、控制器和 GameMode 继承射击模板；敌人、武器与投射物继续复用模板。
- 出生点左前方有低障碍翻越测试，面向并靠近后按空格优先翻越，其余情况下空格跳跃；编辑器连接样例集中在 [Tools/EditorSetup](Tools/EditorSetup/README.md)，当前 Codex 项目配置保留在根目录。
- 最新三阶段流程已生成并保存，验证范围见[本轮记录](docs/qa/narrative-prototype-validation.md)；当前为灰盒原型，未包含完整剧情、美术制作或跨进程存档。

## 文档导航

| 文档 | 用途 |
| --- | --- |
| [原型游玩与开发说明](docs/prototype-play-guide.md) | 运行、按键、正常通关、GM 与构建命令 |
| [实现验证记录](docs/qa/prototype-implementation-validation.md) | 实际通过的检查、验证方式及未覆盖范围 |
| [模板能力盘点](docs/engineering/template-inventory.md) | 已验证资产、实际地图配置、复用注意点与可玩原型缺口 |
| [GM 配套工具范围](docs/design/gm-prototype.md) | 与真实交互共同实现的五类调试操作及边界 |
| [蓝图与 C++ 技术路线](docs/engineering/blueprint-cpp.md) | 当前纯蓝图选择、职责划分与后续引入 C++ 的条件 |
| [游戏需求与原型关卡](docs/design/game-design.md) | 当前完整可玩目标、流程图解读及关卡建议 |
| [阶段循环与世界重置](docs/design/stage-loop.md) | 阶段推进时机、状态模型、重置范围与异常规则 |
| [监控摄像机黑入](docs/design/camera-hacking.md) | 连接、切换视角、转向、退出及循环联动 |
| [工程落地计划](docs/engineering/prototype-plan.md) | 仓库现状、建议职责划分、实现顺序与完成标准 |
| [原型验收清单](docs/qa/prototype-acceptance.md) | 正常游戏流程与 GM 工具的双入口验收 |
| [待决策事项](docs/open-decisions.md) | 需要团队确认的选择、建议和影响 |
| [领域术语](CONTEXT.md) | 统一“阶段”“循环”“初始状态”等概念 |
| [代理协作约定](AGENTS.md) | 后续代理在本仓库工作的规则 |

设计文档中的“已确认”来自项目需求；“建议”或“暂定”是供原型落地使用的方案，尚未代替团队决策。未决项统一以 `D-xx` 编号维护。

## 打开与验证

使用 UE 5.8 打开 [OFFAIR.uproject](OFFAIR.uproject)，默认进入原型地图；点击 Play 后点击游戏视口取得输入焦点。

在工程根目录运行 `Tools/Run-Unreal.ps1 -Mode Build` 可重新生成脚本管理的原型资产，运行 `Tools/Run-Unreal.ps1 -Mode Test` 可执行 PIE 集成验证。重新生成会覆盖受管理的蓝图函数和关卡对象，详见游玩与开发说明。

文档与玩法迭代需同步维护验收清单。功能完成情况以实际编辑器或构建验证记录为准；“计划检查”不等于“已通过”。
