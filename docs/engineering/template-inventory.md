# OFFAIR 模板能力盘点与可玩原型缺口

盘点日期：2026-10-18。当前目标是完整可玩的原型，真实游戏交互与 GM 一起实现；GM 负责调试和快速复现，不能替代正常游玩流程。此前“本期只做 GM”的范围已被本轮要求取代。

本文件记录实现前的模板基线（提交 `39751c5`）。后续新增能力、默认地图和实际测试结果以[游玩说明](../prototype-play-guide.md)与[实现验证](../qa/prototype-implementation-validation.md)为准，不把本页历史缺口当作当前未实现清单。

## 结论

工程已经包含一套有实际蓝图逻辑的 FPS 模板：射击角色、血量与死亡、三种武器、武器拾取、投射物伤害、敌人 AI、出生生成器和 HUD。应以 `Variant_Shooter` 为复用基础，重点补充阶段循环、关键物品与条件、可黑入监控及完整关卡流程。

默认启动地图仍是基础第一人称地图 `Lvl_FirstPerson`。射击内容位于 `Lvl_ArenaShooter`，其地图级 GameMode 覆盖为 `BP_ShooterGameMode`。直接运行默认地图不能代表射击模板缺少功能。

## 验证依据与限制

使用本机 UE `5.8.3-58210709` 的无界面 Python commandlet 加载资产，读取 19 个关键蓝图的继承、默认值、函数、事件以及 59 张图表的节点和连线，并进行内存编译。19 个蓝图均返回编译成功，两张地图均加载成功。没有保存资产、修改项目插件设置或调整默认地图。

这次确认的是资产结构、静态逻辑、编译和地图加载；未进行实际操作的 PIE 射击、敌人寻路、死亡重生或打包试玩。已有历史日志只显示基础 `Lvl_FirstPerson` 的 PIE 启动记录，不能用它证明 Arena 战斗已经试玩通过。

Arena 加载时出现 RecastNavMesh 序列化 `maxTiles` 不匹配并重建的警告；运行时寻路仍需验证。本次 commandlet 汇总为 0 个错误、1 个警告，不把导航警告判为已经确认的玩法故障。

可追溯数据见[盘点证据 JSON](evidence/template-inventory-2026-10-18.json)，包含资产文件与哈希、编译结果、默认值、关键节点摘录、地图对象和输入映射。原始导出及临时检查脚本保留在被 Git 忽略的 `Saved/InventoryAudit/`。

## 可复用能力

以下路径相对仓库根目录。表中“已确认”均指上述静态与编译层面的确认。

| 能力 | 主要资产 | 已确认内容 | 原型处理建议 |
| --- | --- | --- | --- |
| 基础第一人称 | `Content/FirstPerson/Blueprints/BP_FirstPersonCharacter.uasset` | 继承 Character，包含 Move、Aim 和基础跳跃／触摸输入相关图表 | 保留其移动观察基础 |
| FPS 玩家 | `Content/Variant_Shooter/Blueprints/BP_ShooterCharacter.uasset` | 继承基础第一人称角色；当前／最大 HP 默认 500；拥有武器列表、当前武器、开火、切枪、后坐力、伤害与 Die 逻辑 | 作为玩家基础，适配死亡入口与阶段出生配置 |
| 玩家控制器 | `Content/Variant_Shooter/Blueprints/BP_ShooterPlayerController.uasset` | 继承基础控制器；安装武器输入、更新 HUD；绑定角色销毁事件并生成、控制新玩家 | 复用输入和 HUD，替换与阶段重置冲突的自动重生 |
| 游戏模式 | `Content/Variant_Shooter/Blueprints/BP_ShooterGameMode.uasset` | 默认使用射击角色／控制器，含出生点选择、队伍计分、生成敌人判断；本地玩家数量默认 1 | 复用基础配置；竞技场计分不等于解谜通关条件 |
| 武器系统 | `Content/Variant_Shooter/Blueprints/Pickups/BP_ShooterWeaponBase.uasset` 及 `Weapons/` | 手枪、步枪、榴弹发射器均有具体子蓝图；含激活、停用、射击间隔、半自动／自动和投射物生成 | 首个关卡选一种即可，不重做整套枪械 |
| 武器拾取 | `Content/Variant_Shooter/Blueprints/Pickups/BP_ShooterPickup.uasset`、`DT_WeaponList.uasset` | 重叠后调用 Add Weapon Class；隐藏／关闭碰撞后按计时器恢复；数据表包含三种武器映射 | 可直接用于枪械获取；关键任务物品需另定义语义 |
| 伤害与投射物 | `Content/Variant_Shooter/Blueprints/Pickups/Projectiles/` | 基类命中流程包含 ApplyDamage、物理冲量、噪声及爆炸分支；默认 Damage 为 25 | 复用伤害路径，验证射手、本体及关键敌人的事件归属 |
| 敌人角色 | `Content/Variant_Shooter/Blueprints/AI/BP_ShooterNPC.uasset` | 继承基础第一人称角色；HP 默认 100、默认持手枪、队伍值 1；可在放置或生成后自动受 AI 控制；有受伤、射击与死亡事件 | 复用敌人及死亡信号，补关键条件／掉落规则 |
| 敌人 AI | `BP_ShooterAIController.uasset`、`ST_Shooter.uasset`、`ST_Shooter_ShootAtTarget.uasset`、EQS 与 StateTree 任务 | 控制器引用主 StateTree；树包含搜索、移动、调查、攻击和死亡状态，攻击分支运行射击子树 | 保留基础行为，实测导航、发现玩家与攻击；无需先写新 AI 框架 |
| 敌人生成器 | `Content/Variant_Shooter/Blueprints/AI/BP_ShooterNPCSpawner.uasset` | 有开局生成判断、初始延迟、总生成计数和死亡后再次生成分支 | 让阶段系统统一管理生成，GM 共用同一登记与清理入口 |
| HUD | `Content/Variant_Shooter/UI/` | 射击界面、弹药计数和队伍分数显示；控制器含受伤及弹药 UI 更新入口 | 复用战斗反馈，另补阶段、交互目标和监控退出提示 |
| 场景基础 | `Content/LevelPrototyping/` | 灰盒模型、自动门、跳台和靶子；门含 Open Door、Close Door 和重叠事件 | 复用场景资产；自动门需要适配解谜锁定规则 |

## 实际地图配置

| 地图 | GameMode 覆盖 | 本次加载可见的关键对象 |
| --- | --- | --- |
| `Content/FirstPerson/Lvl_FirstPerson.umap` | `BP_FirstPersonGameMode` | 1 个 PlayerStart，主要为基础灰盒环境；未列出射击拾取物和敌人生成器 |
| `Content/Variant_Shooter/Lvl_ArenaShooter.umap` | `BP_ShooterGameMode` | 6 个 PlayerStart、5 个武器拾取点、2 个敌人生成器、1 个门、5 个跳台、5 个靶子，以及 NavMeshBoundsVolume 和 RecastNavMesh |

Arena 五个拾取点实际配置为两把手枪、两把步枪和一把榴弹发射器；Actor 标签中虽有 `Rifle`，具体武器以 `Weapon Type` 数据表行配置为准。两个敌人生成器均为开局生成开启、初始等待 5 秒、`Spawn Count=1`、`Respawn Delay=5`。敌人由生成器在运行时创建，因此静态地图 Actor 列表中没有现成敌人不代表没有 AI。

## 输入与武器配置

输入配置已使用 Enhanced Input。本地资产导出确认：WASD／方向键移动、鼠标观察、空格跳跃、鼠标左键射击、**左 Shift 切枪**；另有手柄与触摸支持资产。不能默认把左 Shift 当成冲刺，也未发现专门的 `IA_Interact` 或手动换弹输入资产。

| 武器 | 弹匣／当前弹数默认值 | 开火模式 | Refire Rate |
| --- | --- | --- | --- |
| 手枪 | 10 | 半自动 | 0.25 秒 |
| 步枪 | 40 | 全自动 | 0.1 秒 |
| 榴弹发射器 | 5 | 半自动 | 0.5 秒 |

`Fire Bullet` 中已连接的流程会递减弹数，并在弹数不大于零时直接将当前弹数设为 Mag Size。因此这里的弹匣显示不代表已经具备有限备弹或手动换弹系统。原型可以先保留该模板行为，只有谜题或战斗确需弹药资源限制时再扩展。

## 接入阶段循环时必须处理的地方

1. **玩家自动重生**：`BP_ShooterCharacter.EventGraph` 的 Die 分支包含 5 秒 Delay 后 Destroy Actor；`BP_ShooterPlayerController.EventGraph` 的 `OnDestroyed_Event` 再生成硬编码的 `BP_ShooterCharacter` 并 Possess。需要改为由阶段流程负责重建，且正确生成项目角色，避免双重重生与丢失项目子类。
2. **敌人生成预算**：Spawner 的 `On NPC Died` 会递减 Spawn Count，仅剩余值大于零时才经过 Respawn Delay 再生成。当前默认值 1 表示默认每个生成器只生成一次，不能误报为无限刷怪；但该分支和延迟任务仍要纳入阶段清理。
3. **拾取点自行恢复**：武器拾取点的 Spawn Time 默认 4 秒。它适合竞技场补给，不能直接用来表示“一次性的阶段关键物品”；对应计时器也不能穿越重置继续改变新世界。
4. **竞技场计分与自动门**：击杀计分、出生点分配和自动开门都已有模板规则；阶段推进、固定出生点及解谜锁门需单独接管，不能将模板行为默认视为满足设计。
5. **监控控制与本体输入**：现有 CameraManager 属于第一人称玩家相机，未发现专用可黑入监控资产。新增远程视角时必须统一停火、输入转移、退出以及死亡／GM 跳阶段中断。

## 从模板到完整可玩原型仍缺什么

| 缺口 | 正常游玩入口 | 对应 GM 能力 |
| --- | --- | --- |
| 阶段管理与全世界重置 | 玩家死亡；已达成条件则下一次复活进入新阶段 | 点击死亡、强制前后阶段切换 |
| 关键条件与进度 | 真正拾取指定物品或击杀指定敌人；条件只标记待生效阶段 | 注入或快速准备测试状态；不能代替真实链路验收 |
| 关键道具与基本交互 | 可拾取对象、明确提示、必要的权限或机关交互 | 快速获取测试条件；具体扩展不默认增加到现有五类清单 |
| 监控设备与黑入 | 玩家能够通过可到达的交互入口连接、转向、退出 | 一键接入同一监控系统 |
| 完整关卡与结束条件 | 从起点通过循环、短战斗、监控解谜到达明确终点 | 前后阶段定位、增减敌人以复现问题 |
| 运行与打包验证 | 不开 GM 完整通关，多次死亡与重置无状态残留 | GM 操作与正常玩法交替执行仍保持一致 |

目前没有发现项目专用阶段、关键物品进度或监控黑入的实现。首个完整原型仍可控制在一张灰盒、两个阶段、一个短战斗和一处监控谜题；关键是正常操作能够走通全程，GM 与之共用核心逻辑。

## 建议的实施起点

先在 `Lvl_ArenaShooter` 做实际 PIE 冒烟检查，验证取枪、射击、敌人移动攻击、受伤死亡和模板重生。随后建立项目专用玩家／控制器／GameMode 与小型关卡，复用已确认的模板能力，接入阶段循环和 GM；再补关键交互与监控谜题，完成不用 GM 的通关验收。

这次是盘点与范围纠正，没有实现上述缺口。蓝图加载、图表读取和内存编译通道现已验证可用，但还不能据此声称复杂蓝图改写、实际玩法和打包流程都已验证。
