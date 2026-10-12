# 维护与发布

本页命令适用于完整源码包，精简插件包不包含开发测试工具。Python 3.10+。运行时脚本仅用标准库。开发结构检查需要 PyYAML，可选的 manifest schema 检查需要 jsonschema（`validate_library.py --schema 本地schema文件`）；依赖见源码根目录 requirements-dev.txt。

```text
python -m pip install -r requirements-dev.txt
python -X utf8 scripts/validate_library.py
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/build_release.py --out ../deep-learning-skills-dist/0.2.0
```

发布默认写入本库旁的 `deep-learning-skills-dist`，包含源码包、双技能插件包、单技能包和 SHA256SUMS。建议每版使用独立 --out 目录；已有同名 ZIP 或 SHA256SUMS 都会拒绝覆盖，单改版本不会覆盖旧校验清单。包里不含 build、缓存、课程目录、第三方全文或机器专属路径。

两项技能的宿主适配参考保持一致，但各自独立包含，安装其中一个不依赖另一个的目录。修改后同时更新这两个文件。题库在 scripts/build_question_bank.py 中维护，运行后生成教授 references/questions；其顺序不是访谈顺序。

教学资源修改保留语境、来源与限制，尤其不要把技巧再写成必做环节。操作协议可以明确先后，正文组织保留判断。新增约束先说明它解决什么实际问题，再用真实案例检查是否过度限制。

脚本协议发生不兼容变化时提高 workspace_format 或 schema，提供迁移方法并保留原课程；不能靠重新 init 清空旧目录。状态中的确认引用只证明文件可找到，真实性仍由实际会话判断。

测试产生明确标记的合成工作区，不包含真实教材和学习者记录。临时目录在 build/test-workspaces 下，清理前检查其绝对路径位于测试目录。单元测试覆盖文件不变量；模型表现、视觉效果和学习深度看真实验收。
