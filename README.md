# wrong-notebook-question-bank

智能错题本（[margrop/wrong-notebook](https://github.com/margrop/wrong-notebook)）的共享题库下载仓库。

题库按学段、学科打包为 JSON。应用中的「真题库」页面可直接从本仓库下载并导入，导入的题目默认只进入真题库、不进入错题本；也可选择同时写入错题本。举一反三练习可按知识点从已导入的真题库中选题。

## 下载与导入

1. 在应用「真题库」页选择「从共享题库下载」，读取 `index.json` 后按包导入。
2. 或下载 `banks/<package-id>.json`，在「真题库」页上传导入。
3. 单包上限 5000 题；包内题目共用 `meta.stage` / `meta.subject`，单题可覆盖。

索引文件：[`index.json`](./index.json)。每个包记录 `file`、`sizeBytes`、`sha256`，应用可按校验值确认文件完整性。

## 数据格式

题库文件为 `wrong-notebook-question-bank` v1：

```json
{
  "format": "wrong-notebook-question-bank",
  "version": 1,
  "meta": {
    "id": "taxonomy-primary-math",
    "title": "数学题库（小学）",
    "stage": "primary",
    "subject": "math",
    "grades": [1, 2, 3, 4, 5, 6],
    "count": 1136,
    "tagged": true,
    "source": "cn-math-taxonomy",
    "sourceUrl": "https://github.com/xiaoyang111222/cn-math-taxonomy",
    "license": "CC BY-NC 4.0",
    "updatedAt": "2026-11-11"
  },
  "questions": [
    {
      "id": "cnm_p001_q1",
      "stage": "primary",
      "subjectKey": "math",
      "grade": 1,
      "semester": "上",
      "questionType": "fill_blank",
      "difficultyStars": 2,
      "text": "3 的后面一个数是几？",
      "options": null,
      "answer": "4",
      "analysis": "从 1 往后数，3 的后面是 4。",
      "knowledgePoints": ["1到5各数的认识"],
      "source": "一年级上册 第1单元 5以内数的认识和加、减法",
      "figureSvg": null
    }
  ]
}
```

字段说明：

| 字段 | 说明 |
|---|---|
| `stage` | `primary` / `junior_high` / `senior_high` / `university` |
| `subject` / `subjectKey` | `math` / `english` / `chinese` / `science` / `physics` / `chemistry` / `biology` / `history` / `geography` / `politics` |
| `grade` | 1–6 小学，7–9 初中，10–12 高中；高中选必册次统一记为 12 |
| `semester` | `上` / `下`；高中真题可空 |
| `questionType` | 应用标准题型：`single_choice`、`multiple_choice`、`true_false`、`fill_blank`、`calculation`、`solution`、`reading`、`cloze`、`writing`、`other` |
| `difficultyStars` | 1–5，可空 |
| `options` | 选择题选项对象 `{"A":"…","B":"…"}`，可空 |
| `knowledgePoints` | 知识点名称数组；应用按名称与错题的知识点标签匹配选题 |
| `figureSvg` | 题目配图 SVG，可空 |

索引为 `wrong-notebook-question-bank-index` v1，`packages` 数组字段与 `meta` 一致，另含 `file` / `sizeBytes` / `sha256`。JSON Schema 见 [`schema/question-bank.schema.json`](./schema/question-bank.schema.json)。

## 现有题库包

| 包 | 学段 | 学科 | 题数 | 知识点 |
|---|---|---:|---:|---|
| `taxonomy-primary-math` | 小学 | 数学 | 1136 | 有 |
| `taxonomy-primary-english` | 小学 | 英语 | 1100 | 有 |
| `taxonomy-primary-chinese` | 小学 | 语文 | 1976 | 有 |
| `taxonomy-primary-science` | 小学 | 科学 | 1040 | 有 |
| `taxonomy-primary-politics` | 小学 | 道法/政治 | 636 | 有 |
| `taxonomy-junior_high-*` | 初中 | 数学、英语、语文、物理、化学、生物、历史、地理、政治 | 5115 | 有 |
| `taxonomy-senior_high-*` | 高中 | 数学、英语、物理 | 2828 | 有 |
| `gaokao-senior-high-*` | 高中 | 数学、语文、英语、物理、化学、生物、历史、地理、政治 | 3126 | 无 |

完整清单与题数见 `index.json`。当前共 26 个包、16957 道题。

## 来源与许可

- `taxonomy-*`：来自 [xiaoyang111222/cn-math-taxonomy](https://github.com/xiaoyang111222/cn-math-taxonomy)，按该仓库 `data/topics.json` 的 `topicId` 补知识点名称，许可 **CC BY-NC 4.0**（非商业使用；商业使用需向原作者单独授权）。
- `gaokao-*`：来自 [rainewhk/gaokao](https://github.com/rainewhk/gaokao)，该仓库整合 [GAOKAO-Bench](https://github.com/OpenLMLab/GAOKAO-Bench) 与 GAOKAO-Bench-Updates，许可 **Apache-2.0**；题目版权归原出题机构。
- 本仓库的打包脚本与索引结构采用 MIT 许可，题库数据沿用各来源许可。详见 [`NOTICE.md`](./NOTICE.md)。

题目、答案与解析由上游项目整理，**不保证**完全准确；用于教学前请核对。上游明确说明其知识图谱与题库仍需一线教师审核。

## 校验

```bash
python3 scripts/validate.py
```

校验索引、包内 `count`、`sha256`、必填字段与题型取值。

## 贡献

新增题库包时：

1. 按 v1 格式生成 `banks/<id>.json`，`meta.count` 与 `questions` 长度一致。
2. 更新 `index.json` 的 `sizeBytes` 与 `sha256`。
3. 在 `NOTICE.md` 记录来源、许可与获取日期。
4. 运行 `python3 scripts/validate.py`。
