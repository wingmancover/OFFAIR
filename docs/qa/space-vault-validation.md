# 空格统一跳跃与翻越验证

2026-10-20，用户确认取消独立 V 键：空格在符合翻越条件时优先翻越，其余情况普通跳跃。保存获授权，Git 操作由用户处理。

## 实现

- 新增项目输入资产 `IA_ContextJump`、`IMC_Traversal`，仅映射空格。优先级 100、消费输入，覆盖同一物理键的模板跳跃映射，原模板资产不改。
- 控制器仅在 Started 调用 Director 的 `JumpOrVault`；先尝试完整安全翻越，未启动才调用模板 Jump。Completed/Canceled 停止跳跃；移除 V 绑定。
- 每轮初始化幂等添加同一映射，不复制映射实例。远程、GM、纸条锁定、重置、完成和翻越过程中拒绝新的空格动作。原有死亡与阶段重置继续清理翻越状态。
- 障碍标牌、HUD 提示和底部说明改为空格。定向编译保存 Director、控制器和 HUD，增量更新标牌，没有重建灯光或布局；纸条位置与盒子尺寸保持用户原值。

## 实测

- [13 项翻越检查](evidence/space-vault-input-result.json)通过。真实长按空格 2.5 秒启动一次翻越，期间角色 `pressed_jump` 保持 false，未同时触发模板跳跃；落地后不自动重跳或重复翻越。再次短按空格正常跳跃。其余朝向、距离、遮挡、高度、重复事件、死亡、GM 重置和远程拒绝用例通过。角色摆位与边界场景由 PIE 测试夹具完成，物理空格输入由 Windows 键盘事件完成。
- 在可翻越点实际按旧 V，保持未启动状态；控制器中已无 V 事件绑定。
- [两项额外真实输入检查](evidence/space-vault-fallback-result.json)通过：落点被挡时空格退回普通跳跃；死亡复活后空格仍能成功翻越并落地。
- [完整阶段与监控回归](evidence/space-vault-runtime-result.json) **44 项通过，61.03 秒**。包含无 GM 正常主线、真实战斗、权限卡、直接摄像头黑入、通关，以及隔离的重置、GM 和异常用例。
- 已查看[空格提示](evidence/space-vault-prompt.png)与[更新后的底部说明和落地画面](evidence/space-vault-landed.png)。HUD 编译通过，Python 语法、文档链接及 Git diff 检查通过。

最终编辑器停在 `Lvl_Prototype`，PIE 已结束，资产已保存；[最终状态](evidence/space-vault-final.json)记录物体保留和未保存包检查。没有执行打包、手柄或触屏输入验证；本轮仅统一键盘空格操作。
