# 编辑器连接配置

这些配置是编辑辅助工具的 Unreal MCP 连接，不参与游戏运行或打包。

- 根目录 `.codex/config.toml` 保留，供本项目当前使用的 Codex 自动读取；没有更改用户全局设置。
- 其余四份配置已从根目录集中到 `Templates/`，保留原内容。样例在这里不会被相应客户端自动加载；需要使用时，代理执行 `Restore-Connection.ps1 -Client Cursor|Gemini|VSCode|Generic` 恢复对应约定路径，恢复出的本地文件由 `.gitignore` 排除。
- 恢复脚本遇到已有配置会停止，避免覆盖组员自定义设置。没有配置密钥，地址均为本机 `http://127.0.0.1:8000/mcp`。
- Windows“隐藏”属性只影响本机文件浏览，不会让 GitHub 首页隐藏已跟踪文件。本次通过移动实际文件减少根目录项目；GitHub 上的变化需用户自行提交和推送后生效。

Codex 项目配置的路径依据：[OpenAI 官方配置说明](https://learn.chatgpt.com/docs/config-file/config-basic)。组员仍可按需要选择其他客户端，样例没有被删除。
