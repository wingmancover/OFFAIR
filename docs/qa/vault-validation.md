# 简单翻越与配置整理验证

基线：用户已上传的 `5ee92c2`。本轮授权保存，不暂存、不提交、不推送。规则见[低障碍翻越](../design/vault-prototype.md)。

## 资产与实现

定向生成并编译、保存 `BP_RunDirector` 和 `BP_OFFAIRController`，增加 V 键翻越、胶囊扫掠及清理入口。地图增量增加 `OF_VaultObstacle`、`OF_VaultSign` 和 Director 引用，没有重建灯光、纸条、盒子或原模板资产。作者脚本同步。

Anchor 仍为位置 `(1005,190,0.3)`、缩放 `(0.55,0.38,0.002)`；盒子仍为位置 `(820,0,65)`、缩放 `(0.7,0.6,1.3)`，构建前后检查一致，见[构建结果](evidence/vault-build.json)。

## 游戏验证

1. **翻越定向检查 12 项通过**。夹具把角色放到障碍前，实际 Windows V 键启动，越过后落地恢复行走；最高胶囊中心高度约 224 cm。随后实际空格仍能跳跃。其余用例涵盖朝向错误、距离过远、重复触发、落点遮挡、头顶遮挡、障碍过高、中途死亡、GM 切阶段和远程模式拒绝，见[输入与边界结果](evidence/vault-input-result.json)。碰撞夹具仅临时修改 PIE 中的掩体，不保存地图。
2. **完整阶段与监控回归 44 项通过，60.86 秒**。正常路线未用 GM 跳阶段，真实拾条、系统死亡、陷阱敌人投射物死亡、拾枪战斗、掉卡、直接黑入、通关均通过。异常、重置和 GM 用例在正常路线后隔离执行，见[回归结果](evidence/vault-runtime-result.json)。纸条中断夹具改用实际物品引用定位，适应用户已移动的纸条。
3. 导航构建后，出生点、翻越两侧、盒子、守卫和监控通道六处可行走面投影成功，见[导航结果](evidence/vault-navigation.json)。
4. 已查看[实际提示画面](evidence/vault-prompt.png)。最终结束 PIE，地图、蓝图均已保存，物体保留与编辑器状态见[最终检查](evidence/vault-final.json)。没有执行打包或其他平台测试；本轮不包含手部动画、通用墙面攀爬或复杂翻越关卡。

翻越独立验证脚本保存在 `Tools/unreal/validate_vault.py`，等待实际 V／空格输入；不能把脚本调用 `TryVault` 的边界夹具当作物理按键测试。

## 根目录整理

四份配置完整移动到 `Tools/EditorSetup/Templates`，不删内容：Cursor、Gemini、VSCode、通用 `.mcp.json`。`Restore-Connection.ps1` 四个客户端都实际恢复过，SHA256 与样例一致，已有文件的覆盖保护也通过；测试后移除生成的本地副本。原路径加入 `.gitignore`，`.codex/config.toml` 保留原位与原内容，未修改用户全局配置。

GitHub 首页的移除要等用户提交、推送后生效；Windows 隐藏属性不能隐藏远程已跟踪文件。连接路径说明见[工具配置说明](../../Tools/EditorSetup/README.md)。
