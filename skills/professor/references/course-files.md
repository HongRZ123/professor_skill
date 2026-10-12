# 课程文件协议与命令

脚本需要 Python 3.10+ 标准库。先定位本技能目录和课程根目录；下文的路径文字是待替换示意，不是环境变量。Windows 建议加 `-X utf8`。JSON 输入先保存文件，不把用户文字拼成 shell 代码。

```text
python -X utf8 <skill>/scripts/course_state.py init --root <course> --topic <学习对象>
python -X utf8 <skill>/scripts/course_state.py status --root <course>
python -X utf8 <skill>/scripts/course_state.py update --root <course> --expected-revision 0 --patch .operations/update.json
python -X utf8 <skill>/scripts/check_artifacts.py --root <course> --lesson L01
python -X utf8 <skill>/scripts/check_delivery.py --root <course> --lesson L01
python -X utf8 <skill>/scripts/course_state.py publish --root <course> --expected-revision 4 --lesson L01
python -X utf8 <skill>/scripts/course_state.py refresh --root <course> --expected-revision 5
```

示意修订号不能照抄；先读 status，使用真实值。patch 是课程内的相对路径；`.operations` 只在保存操作输入时产生。status/check 不改文件，refresh 仅重建 COURSE.md 的管理区。失败返回非零退出码与具体原因，先处理而非改状态掩盖。

## 状态和阶段

state.json 保存 schema_version 为 `1`、workspace_format 为 `professor-workspace-v1`、稳定 course_id、title、revision、storage_mode、stage、brief、syllabus、active_lesson_id、published_lessons、waiting_for、checkpoint_ref、updated_at。需要时有 return_to 与 action_ref。

brief 和 syllabus 是含 path、version、confirmation_ref 的对象；不存在时为 null。path 指实际文件，confirmation_ref 指保存了用户实际决定的记录，可以带锚点。脚本只检查文件存在，不能证明这句话真由用户说出。

例如需求确认后，先保存简报及用户确认记录，再写 patch：

```json
{
  "stage": "researching",
  "brief": {"path": "intake/brief.md", "version": "b1", "confirmation_ref": "intake/notes.md#decision-b1"},
  "waiting_for": "开展已授权的课程研究。"
}
```

大纲草案阶段需要 research/report.md、knowledge-structure.md、sources.json 和 syllabus 引用。进入 ready 需要简报、大纲实际确认引用，并通过材料包检查：materials/index.md、reading-plan.md、catalog.json、可用主材料和逐课阅读。进入 authoring_lesson 另有 active_lesson_id 和 action_ref，核对当前课材料可用，后者指开始本课的实际用户请求。需求或大纲需修订时先保存新草案、清除不适用的确认引用，退回相应阶段，不让旧确认自动批准新方向。

用户明确授权省略访谈时可以把有限简报与未知保存，再记录该授权进入研究；脚本不要求固定采访轮数。完成课程用 completed 及 action_ref 记录实际收束决定，不登记全面掌握。

更新不得修改 course_id、schema 或 published_lessons；发布指针由 publish 维护。并发时 expected-revision 不符就重读并合并真实变化，不能只取新数字重放旧 patch。锁只覆盖短时保存，不覆盖整个上课过程。

## 来源

research/sources.json 是数组。每条有稳定 source_id、title、origin（原始 URL、DOI 或明确的本地来源）、version、access、read_scope、role；可附 local_path、locators 和 notes。读取范围用具体章节、页面或代码位置，不填“已下载所以已读”。

access 可用 full、excerpt、abstract、unavailable、not_read。摘要可以支持其实际表达的有限主张，不能支持没有读到的证明。unavailable/not_read 的条目可用于研究待办，不能作为发布课次的已读依据。

local_path 使用工作区内相对路径；在外部的用户教材用 external_path 标识外部依赖，脚本不自动遍历或复制。版本与印刷页码由 agent 核对。

## 准备与发布课次

每个课次有稳定 ID，每次实质修订有新版本目录。L01/v1/lesson.md 是正文，L01/v1/assets 保存本版资产；L01/lesson.meta.json 是当前待发布元数据。不要覆盖旧版正文：新版本写到 L01/v2。

元数据例子如下，内容只是结构示意，必须替换成实际阅读、检查和文件事实：

```json
{
  "lesson_id": "L01",
  "version": "v1",
  "syllabus_version": "s1",
  "status": "draft",
  "lesson_path": "lessons/L01/v1/lesson.md",
  "review_ref": "lessons/L01/v1/review.md",
  "source_ids": ["S001"],
  "assets": [],
  "delivery": {
    "standard": "lecture-120-v1",
    "lecture_minutes": 120,
    "callbacks": [{"source_id": "S001", "locator": "实际原文位置", "lesson_location": "正文中实际存在的定位文字"}]
  }
}
```

上例 assets 空数组只是字段示意，不能用于默认完整课堂发布。需填实际制作、嵌入和解说的视觉对象。每项记录 path、kind、purpose、provenance、checked；kind 为 generated-image、source-image、data-chart、diagram、interactive 或 other。数据图还需 data_path 与 script_path；交互需 fallback_path；行内 Mermaid 的 embedded_anchor 及例外规则见[交付约定](delivery-contract.md)。路径相对课程根。实际查看才写 checked 为 true。

素材按本文协议准备后，check_delivery 核对材料、正文量、回读定位和视觉嵌入；check_artifacts --lesson 和 publish 也执行同一交付检查。正文过短或主要交付缺失时不得发布，继续增补本课。agent 另做内容审阅。publish 将 metadata 置 complete，保存版本元数据、文件哈希、来源及材料地图快照，最后更新阅读入口。它不调用模型、不评定内容、不证明用户收到或读懂。

同版本内容不同不能重复发布，改成新版本。审阅记录、资产及其数据、脚本、后备文件均保存在对应课次版本目录中，不覆盖旧版。来源登记表与普通资料链接保存发布时快照，允许它们在课程推进中继续维护；实时哈希冻结的只有课次版本目录里的发布文件。旧版仍可以在其版本目录阅读。关键修改原因由 agent 写入 changes.md。

检查覆盖本地文件、路径、来源身份、读取范围字段、材料取得记录、版本、部分 Markdown 链接、粗略正文量、教材对读定位与视觉嵌入。不能验证远程内容、所有 HTML/CSS 依赖、所有锚点、引文语义、实际同意或图像正确性。以脚本错误作具体定位，不能以通过替代教学审阅；达到字数与最低视觉要求不等于讲透或视觉丰富。

## 用户记录和私教

learning/record.md 保存有证据身份的真实事件，questions.md 保存未解决问题；用户笔记不默默改写。教授整理 handoff/tutor-context.md；私教独立追加 handoff/from-tutor 报告，教授在 changes.md 引用反馈 ID 记录处理。

私教反馈必须对应实际发布的课次版本；脚本接受当前版或有发布快照可核对的旧版。若用户在读旧版，明确差异，保留他们真正的问题，再由教授决定回写位置，不能谎改反馈版本。

## 中断与未知版本

初始化中断可再次 init，根据已有日志恢复，遇到不同内容会保留并报冲突。课次完整文件与发布指针可能在中断时不一致，status/check 会报告部分情况；核对实际文件后完成未完发布，不把孤立文件当已交付。

state 已写而 COURSE 导航未刷新时，可在核实后 refresh。未知格式不自动迁移；先保留原件。脚本升级不改变课程目录。会话文件模式在离开前交付真实文件归档，保持单个正式写入者。
