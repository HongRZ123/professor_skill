# 安装与加载

技能安装位置和课程工作区是两回事。先让宿主发现技能，再在选定课程目录中使用。不要同时安装同名独立技能和插件副本，否则选择器可能出现重复项。

## Codex 的独立技能

从 [GitHub 仓库](https://github.com/HongRZ123/professor_skill)下载 ZIP 并解压，或执行 `git clone https://github.com/HongRZ123/professor_skill.git`。在源码根目录下运行：

```powershell
python -X utf8 scripts/install_skills.py --user
```

这会复制 professor 和 course-tutor 到用户的 `.agents/skills`。只装教授可加 `--skill professor`。若希望仅某个项目可用，改为明确的目标路径：

```powershell
python -X utf8 scripts/install_skills.py --dest '你的项目目录/.agents/skills'
```

`--dest` 示例须替换。安装脚本只复制本库技能，遇到已有目录会完整停止，不删除或自动升级；先比较现有版本、另行备份再决定更新。它不会更改客户端配置或绑定当前聊天。

不使用脚本时，将发布包中的整个 professor、course-tutor 文件夹复制到实际技能发现目录；不能只复制 SKILL.md。官方当前列出的用户目录为 `~/.agents/skills`，项目目录为 `.agents/skills`。旧版客户端使用其他目录时，以其实际文档和发现情况为准，不自动双份安装。

安装后在技能选择器查看名称和路径。在 Codex 可明确提及 `$professor` 或 `$course-tutor`；具体桌面 UI 以其选择器为准。CLI/IDE 的 `/skills` 不是所有桌面产品通用指令。ChatGPT 使用 `@` 选择技能；若界面入口不同，先查看实际可选项。[官方加载与调用说明](https://learn.chatgpt.com/docs/build-skills)

## ChatGPT / Codex 插件包

`deep-learning-skills-0.2.0-plugin.zip` 中只有一个插件根目录，含 portable `plugin.json`、skills 及使用说明。由支持该格式的插件导入或本地 marketplace 流程接入；具体账号是否提供入口需实际核实。源码包用于修改和开发，不必把测试和开发脚本上传为运行资源。

桌面本地插件可参考[官方安装说明](https://developers.openai.com/plugins/build/plugins)。本库未注册 marketplace、修改个人配置、上传账号或发布插件。本地源码可加载与账号插件安装成功是不同验证结果。

没有插件入口但能加载独立技能的桌面环境可用上一节；只有普通文件上传的聊天不能被描述为已安装技能。若确实只能提供文件，需让 agent 明确读取入口和按需参考，并接受该模式没有原生发现保证。

## 开课和恢复

选一个独立、可写的课程目录，让教授使用当前目录并给出 topic。第一次同轮完成最小初始化与访谈；再调用时读取已有 COURSE.md、state.json，不重复开课。课程材料随使用按需增长，不预建空的整套课程。

另一个聊天只有能访问同一目录时才共享状态。ChatGPT 会话沙箱模式需下载完整课程归档，在新聊天提供归档；私教反馈也需实际文件交接。课程路径和技能路径都不是自动跨机器同步的云标识。

## 验证安装

在一个新的空测试目录选择教授，提出一个测试学习主题。预期出现课程入口和少量具体访谈问题，不应立即生成大纲或整套课程。关闭这一轮后重新请求继续，应读取原状态而不是重新初始化。安装检查到这里即可，真实课次质量另按[行为验收](behavior.md)核对。
