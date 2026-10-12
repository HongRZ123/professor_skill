# 研究来源与复用取舍

本库基于本次需求访谈、教授详细设计、课堂文字稿比较和开源项目实际文件研究独立编写。随包教学札记是研究分析，不是完整课堂转写；未打包用户教材、上游完整技能或第三方论文全文。

## 开源工作流参考

以下为设计研究固定的版本，后续上游可能变化。研究看过实际指令、参考、脚本和部分示例，未把 README 宣传当成已运行能力。

| 项目与固定提交 | 本库借鉴 | 没有继承 |
| --- | --- | --- |
| [sijiao-skill · ef4508b](https://github.com/swaylq/sijiao-skill/tree/ef4508bfd885e0abb46392c7d43d8dde5014f00b) | 稳定来源身份；课程、研究、学习状态分开；文件工具 | 主题专属技能生成器、固定发展阶段、强制项目、覆盖式安装 |
| [anything-to-course · f11bbf2](https://github.com/lowwwbank/anything-to-course/tree/f11bbf21572a9864759929946c2c3da6857e1744) | 用实物课次校准体验；材料按职责组织 | 每课固定流程、用户请求解释时仍强制先尝试 |
| [learn-anything-skill · b4d6f9c](https://github.com/koganei/learn-anything-skill/tree/b4d6f9ca94129c4a5beedfbd0d44b77affb8d948) | 初始领域研究与课次补研分开、按需保存 | Claude 专属工具假设、每小段暂停、固定技术课型 |
| [book-tutor · 6d98d5b](https://github.com/xixiaofinland/agent-skills/tree/6d98d5ba75f4bd50dda4a1f3f63c87a00e19cec8/skills/book-tutor) | 开始恢复、结束保存、有价值才记概念笔记 | 以短问答替代完整课堂、强制苏格拉底式提问 |

上游测试通过不计为本库测试。对 sijiao 的部分工具做过独立执行；其余项目主要是指令与产物阅读。研究没有验证任何一个上游完整长期课程效果。本库未复制这些项目代码或长篇指令；未假定不同仓库的许可证相同。

## 真实课堂与教育研究

教学资源来自 MIT OCW、Open Yale Courses 的文字稿比较，以及教学知识、知识组织、课堂话语和大学教学指导研究。详见[教学依据与实际阅读范围](../skills/professor/references/teaching/research-basis.md)。

保留两层材料：领域札记解释语言怎样贴近该领域的对象和证据；案例保留教师在特定位置怎样推进理解及其语境。通用参考说明教学功能，不将开场、展开、推进、结课固化为正文栏目。

## 宿主组织方式

核对日期：2026-10-12。入口与配套资源采用 [OpenAI 技能结构](https://learn.chatgpt.com/docs/build-skills)；双技能分发采用[官方 portable 插件结构](https://developers.openai.com/plugins/build/plugins)。两项技能 UI 元数据由本机官方 skill-creator 工具生成并校验。库中不包含 OpenAI 工具代码的复制件。

本库以技能与标准库文件工具落地，不建立新的 MCP、数据库或后台代理系统。原创代码、指令与研究分析由 HongRZ123 选择以 [MIT 许可证](../LICENSE)发布。第三方引用保留来源和范围；仓库的许可证不延伸到外部教材、完整课堂稿、论文或上游项目。
