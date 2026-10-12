# 完整课堂的交付约定

本约定约束材料准备和成品分量，不规定讲授内容的顺序。标准为 lecture-120-v1：每课完整 120 分钟讲授量；周预算影响每周课程数与阅读节奏。中文编写预算 24,000–32,000 个实质文字单位，程序最低线为 24,000。汉字按字符、外语按完整词计；这是防止短稿误发布的工程计量，不是大学教师语速研究，也不证明实际授课时长或深度。

程序计数去掉代码块、标题、表格行、块引文、图片、链接目标和 HTML 标签。它仍不能自动区分原创解释和重复套话，agent 必须排除充量行为。例题推导与图像解说属于主讲正文；附件、书目、学生自主阅读和练习时间不能补课堂量。

用户明确要求短讲、复习摘要或其他规格时，可以执行该请求，在元数据使用 delivery.override 记录 confirmation_ref、reason、lecture_minutes 和 min_prose_units。不能用周预算、赶时间或 agent 自己的“用户可能读不完”来填写授权。正文标题和交付说明明确短讲身份，不冒充完整课。一般缺工具也不授权缩短内容。

## 材料目录示意

这是文件字段示例，不是教材选择模板。按真实材料和 syllabus 补全全部课次，课堂和课后阅读各有实际内容。

```json
{
  "materials": [
    {"source_id": "S001", "role": "core", "edition": "实际版本与语言", "availability": "local", "local_path": "materials/files/core.pdf", "access_note": "实际取得与检查说明"}
  ],
  "lessons": [
    {
      "lesson_id": "L01",
      "before": [],
      "before_note": "本课无需先读；课堂中会带读原文。",
      "in_class": [{"source_id": "S001", "locator": "已核实章节与位置", "purpose": "在课堂中重建这一段论证"}],
      "after": [{"source_id": "S001", "locator": "课后回读位置", "purpose": "用本课获得的区分重新理解原文"}]
    }
  ]
}
```

role 为 core、support 或 further。availability 为 local（非空 local_path 文件）、online（实际可用 url，access_note 说明取得与本地保存限制）、user-copy（用户已持有，confirmation_ref 指实际记录）、unavailable（注明缺口）。edition 与 access_note 必需。所有条目引用已登记来源；核心材料不能 unavailable。未来补充材料可暂不可用，但其问题必须可见，当前课安排的阅读必须能取得。

## 课次元数据增量

在原 lesson.meta.json 上增加 delivery；其余字段按[课程文件协议](course-files.md)。

```json
{
  "delivery": {
    "standard": "lecture-120-v1",
    "lecture_minutes": 120,
    "callbacks": [
      {"source_id": "S001", "locator": "具体原文位置", "lesson_location": "正文实际存在的一处小标题或定位文字"}
    ]
  }
}
```

callbacks 记录实质教材讲读的位置，选典型处而非每个引文；必须包含本课阅读地图中的主线材料。正文还需在其他有关位置自然回读，不能填完一项就停止建立联系。

assets 中的视觉对象必须实际嵌入正文：可用 Markdown 图片、相对链接的可视化 HTML 或有可查锚点的行内 Mermaid。行内 Mermaid 的元数据 kind 为 diagram，path 指保存的 Mermaid 源文件，embedded_anchor 指正文紧邻图的真实 HTML 锚点；源代码必须与该处代码块一致。数值图、图片和独立 HTML 等仍按原资产协议保存、检查。

默认正式课应有多个分布在讲述中的视觉对象及充分解说。自动检查只拦截完全没有视觉材料或文件并未嵌入的情况，不把一幅图判为“丰富”。真实工具不可用或用户明确不要视觉时，记录 delivery.visual_exception 的 reason、evidence_ref 与 fallback 文字替代说明；有工具而觉得文字方便，不成立为例外。未完成必要的视觉内容须说明成品缺口。

check_delivery.py 可单独审查；check_artifacts.py --lesson 与 publish 也执行同一检查。旧版已经发布的内容不会被自动重写，但其不达标之处可以用新检查检出。材料就绪检查在进入 ready、开始编课及新发布时执行；旧 state 仍可读取和恢复。
