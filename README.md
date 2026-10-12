# Professor Skill · 深入学习技能库

[![Validate skills](https://github.com/HongRZ123/professor_skill/actions/workflows/validate.yml/badge.svg)](https://github.com/HongRZ123/professor_skill/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

版本：0.2.0。面向 Codex / ChatGPT 的教授与课后私教技能，按标准技能目录组织，可分别安装，也提供双技能插件包。本版针对真实试用中“材料未备齐、课堂偏短、零视觉内容”修订了教授交付要求；见[改动与已有课程接续](docs/upgrade-0.2.md)。

教授负责从深入访谈、资料研究、教材与阅读材料准备、课程大纲到逐课完整讲授；私教围绕实际材料解释疑难。每堂课按完整 120 分钟讲授量编写，周预算决定每周课数；默认分批制作并持续增补同一课堂，包含教材对读和多处视觉解释。课程和学习记录放在独立工作区，教学经验按需参考，不固定每课正文结构。

## 包含什么

| 技能 | 入口 | 作用 |
| --- | --- | --- |
| professor / 教授 | [SKILL.md](skills/professor/SKILL.md) | 采访与确认需求、研究报告、syllabus、完整课堂、视觉材料和课程维护 |
| course-tutor / 课后私教 | [SKILL.md](skills/course-tutor/SKILL.md) | 直接解释、文本或推导讨论、补充前置和有依据的反馈 |

教授资源中有按场景检索的访谈题库、通用教学分析、七个领域窗口及保留语境的真实课堂案例。它们提供判断依据，数量和使用频率不作为教学质量标准。

随包脚本负责初始化、阶段保存、版本、发布检查与私教反馈。发布时增加材料准备、主讲正文量、教材回读定位和实际视觉嵌入的检查。它们拦截明显交付缺失，访谈、来源、教学深度和视觉丰富度仍需实质判断与用户校准。

## 在 Codex 本地开始

需要 Python 3.10+。先克隆仓库，再运行安装脚本，将两个技能复制到用户技能目录。没有 Git 时，也可从仓库页面的 **Code → Download ZIP** 下载并解压，在解压后的根目录运行最后一条命令。

```powershell
git clone https://github.com/HongRZ123/professor_skill.git
cd professor_skill
python -X utf8 scripts/install_skills.py --user
```

安装脚本本身不联网、不覆盖已有同名技能。也可用 `--dest` 指定一个项目的 `.agents/skills`，或加上 `--skill professor` 仅安装教授。文件安装后在客户端技能选择器确认可见；若未出现，重启客户端再查。完整方法见[安装与加载](docs/installation.md)。

在一个用于这门课程的空目录中开启 Codex 聊天，选择教授技能，并提供主题，例如：

> 使用 professor。我想学习“德国古典哲学：从康德开始”。请在当前目录建立课程工作区，先开展访谈。

教授建立最小入口并开始访谈。访谈可跨多轮；需求确认后研究，交付实质报告与大纲草案。大纲确认后准备教材、逐课阅读地图、课程说明和首课预习；确认并要求开始时继续生成第一节完整课堂。以后要求“下一课”才继续，每次一节。

课后在能访问同一课程目录的另一个聊天选择私教，例如：

> 使用 course-tutor，读取当前课程。我在 L01 的这段论证处卡住了：……

私教给出解释，保存有价值的反馈。返回教授时，它读取新增反馈并按影响处理；技能不会自行创建聊天或相互发送消息。文件发布、用户看过与掌握始终分开。

## ChatGPT 的适配范围

本库采用 `SKILL.md + references/scripts + agents/openai.yaml`，并提供根级 `plugin.json`。独立技能和插件的分发入口依据 [OpenAI 技能文档](https://learn.chatgpt.com/docs/build-skills)与[插件打包文档](https://developers.openai.com/plugins/build/plugins)，核对日期为 2026-10-12。

工作区能力取决于实际工具：有持久本地目录时直接维护文件；只有会话沙箱时导出课程归档，由用户带到新聊天；只有文本时明确缺少持久文件能力。插件不会赋予不存在的联网、图像生成或执行权限。上传一个 MD 也不等于安装整套技能。

## 文件组织

```text
plugin.json                 双技能插件入口
skills/
  professor/                可单独安装
  course-tutor/             可单独安装
docs/                       安装、兼容性、研究来源与验证说明
scripts/                    安装、静态检查、题库维护、发布打包
tests/                      文件生命周期与打包测试
.github/workflows/          可复用的 CI 检查配置
```

技能库目录存工作方法；课程目录存用户材料。不要在技能安装目录里开课，也不要把私人学习记录提交进技能库。

详细说明：[预期行为](docs/behavior.md) · [能力边界](docs/compatibility.md) · [研究取舍](docs/research-provenance.md) · [验证结果](docs/validation-results.md) · [维护与打包](docs/development.md)。

当前版本已实现文件工具与教学指令；修订后完整课堂的实际深度、两个新聊天的接续及 ChatGPT 账号内插件加载仍需实际使用验证。文件与脚本检查通过不等于教学质量通过。

## 许可证与来源

本仓库原创代码、指令和研究札记以 [MIT 许可证](LICENSE)发布。引用的教材、课堂、论文、图像和外部项目仍由各自权利人持有；本许可证不为第三方原始材料授予额外权利。仓库只包含方法、来源链接与研究分析，不附带用户的课程记录或第三方完整教材。参考来源和复用范围见[研究说明](docs/research-provenance.md)。
