# 灯光与文字可读性首轮验证

本轮由用户确认先处理曝光、过亮区域与关键文字对比度。用户已调整纸条位置和金色盒子尺寸，本轮保留这些变更；保存获授权，不执行 Git 暂存、提交或推送。开始时工作区还包含上轮五秒对白和用户地图的未提交修改，均保留。

## 实际改动

- 地图新增 `OF_ReadabilityExposure`，全局后处理优先级 10。工程既有扩展亮度范围下，曝光上下限同设 EV100 3，补偿 0；泛光 0.15。保持现有渲染配置与插件。
- 四盏区域点光从 5000 降至 2000，方向光从 3 降至 1.5，天空光 0.6；监控红灯从 8000 降至 2800。监控通道增加 500 强度的冷色弱补光，避免固定曝光后通道过暗。均为可逆的首轮参数，整体氛围待用户试玩确认。
- `BP_PrototypeHUD` 普通文字接近白色；目标区底板加深；只有出现交互文字时绘制与文字宽度匹配的深色底板。远程操作说明也有底板。系统错误和心理对白保留原颜色及三秒／五秒时长。
- 作者脚本 `prototype_hud.py`、`prototype_level.py` 同步。编辑器只重编译 HUD 和增量应用 `update_readability_layout()`，没有运行完整关卡生成或 `update_narrative_layout()`。
- Anchor 位置仍为 `(1005, 190, 0.3)`；盒子位置 `(820, 0, 65)`、缩放 `(0.7, 0.6, 1.3)`。修改前后逐分量校验通过。新增灯光和曝光属于静态地图配置，每次重载恢复同一配置，无新增循环内玩法状态。

## 实测范围

HUD 编译保存成功，地图已保存，见[构建与物体保留检查](evidence/readability-build.json)。Python 语法检查和 Git diff 空白检查通过。

图形 PIE 使用夹具摆放和朝向角色，再通过原生 Windows **E 键**拾取纸条与打开盒子；敌人使用真实投射物击杀玩家，复活进入 S2，生命恢复 500，第二段对白正常显示并消失。最终正常阶段观察通过，见[流程结果](evidence/readability-normal-result.json)。这不是从出生点全程手动步行的验收，未重跑历史 44 项完整回归或打包测试。

监控部分独立使用 GM 进入 S2、伤害夹具击杀守卫，再用实际 E 拾取真实掉落权限卡、看向设备并按 E 黑入。检查投影提示、延迟至视角混合完成后的远程画面，以及正常退出，见[监控结果](evidence/readability-camera-result.json)。该夹具站在探测区内，截图中的警报为正常探测结果，不能视为正常通关测试。

已查看 Unreal 原生 1280×720 截图，确认纸条红色、盒子形状、道路和敌人可辨，提示能与明暗背景区分：

- [出生区](evidence/readability-spawn.png)、[纸条提示](evidence/readability-note.png)、[盒子提示](evidence/readability-box.png)
- [中央错误](evidence/readability-system.png)、[第一次对白](evidence/readability-thought1.png)、[第二次对白](evidence/readability-thought2.png)
- [权限卡](evidence/readability-card.png)、[摄像头提示](evidence/readability-camera.png)、[远程画面](evidence/readability-remote.png)

测试结束 PIE；[最终状态](evidence/readability-final.json)记录物体保留、曝光值与未保存包检查。固定曝光在各阶段共用，最终亮暗舒适度仍由用户试玩确认；不同显示器、其他分辨率、世界标牌整体布局、完整 HUD 精简及翻越不在本次验证范围。
