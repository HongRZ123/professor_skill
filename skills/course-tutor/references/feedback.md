# 与教授交换反馈

先读实际课程入口、state.json 和对应课次。辅导不修改教授拥有的状态、需求、大纲或正式讲义。只为有持续价值的疑难与反馈追加文件，不用格式负担打断学习。

有 Python 时，将本次真实内容写成课程内 JSON，再运行：

```text
python -X utf8 <course-tutor>/scripts/record_feedback.py --root <course> --input .operations/tutor-feedback.json
```

输入字段：lesson_id、lesson_version、material_location、user_question、response_summary、evidence_kind 是必需文本；可加 learner_evidence、unresolved、recommendation。evidence_kind 为 self_report、observed_response、unverified 或 explanation_only。记录用户真正说过或做过的事，不能把示例回答当真实证据。

脚本确认课次版本对应当前发布指针或已有发布快照后，在 handoff/from-tutor 中创建独立 UUID 文件，包含课程身份和时间，不写 state.json。没有出现的表现保留未知。教授会依据反馈做决定，不把建议直接当作已获用户批准的大纲变更。

用户读旧版时，先说明与当前版的关系，用实际旧版本保存；若该版本无法在课程中核实，手工保留注明待核对的反馈，交给教授核实，不能谎改版本让脚本通过。若私教和教授没有同一目录，交付反馈文件给用户带回。

手工格式使用 Markdown，可带 feedback_id、course_id、lesson_id、lesson_version、evidence_kind、created_at 的 frontmatter，正文写材料位置、实际问题、本次解释、学习证据、未解决事项和建议。只写实际有用的内容；无需每个小问题都填满表。

没有教授课程或状态时仍可解答所给材料；如要保存辅导记录，明确这是独立材料记录，不能伪造教授课次和发布版本。
