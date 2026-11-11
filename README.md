# wrong-notebook-question-bank

智能错题本（[margrop/wrong-notebook](https://github.com/margrop/wrong-notebook)）的共享题库仓库。

题库按来源、学段、学科打包为 JSON。应用的「真题库」页可以直接从本仓库下载并导入；导入的题目默认只进入真题库，也可以选择同时写入错题本。举一反三练习会按知识点从已导入的题库中选题。

现有题库见 [`docs/CATALOG.md`](./docs/CATALOG.md)。

## 使用题库

- **在应用里下载**：打开「真题库」页，选择「从共享题库下载」，按包导入。
- **手动下载**：从 [`docs/CATALOG.md`](./docs/CATALOG.md) 找到题库包，下载对应的 `banks/<来源集>/<包 id>.json`，在「真题库」页上传导入。

题目、答案与解析由各来源整理，不保证完全准确，用于教学前请核对。发现错误可以开「题目纠错」Issue 或直接提 PR。

## 把自己的题库转成题库包

手里有 Excel、Word、PDF 或其他格式的题库，可以转换成题库包后导入自己的错题本，不必共享。

**用 AI 编程助手**（推荐）：克隆本仓库，在仓库目录中打开 Claude Code、Codex、Cursor 等助手，告诉它：

> 把 ~/Documents/初二物理题库.docx 转成错题本题库

助手会按仓库自带的技能 [`convert-question-bank`](./.claude/skills/convert-question-bank/SKILL.md) 完成抽取、打包、校验和抽查，并询问你是只自己用还是愿意共享。愿意共享时，它会接着准备 PR。

**手工转换**：把题目整理成 CSV、JSONL 或 JSON 数组（字段见 [`docs/FORMAT.md`](./docs/FORMAT.md#题目)），然后：

```bash
python3 scripts/qbank.py pack 题目.csv --out 我的题库.json --id my-bank \
  --title "我的初中数学题库" --stage junior_high --subject math \
  --source "自己整理" --license "仅供个人使用"
```

工具只需要 Python 3.9 及以上，没有第三方依赖。

## 共享题库

欢迎把自编的题目或开放许可的数据集贡献到本仓库，要求和步骤见 [`CONTRIBUTING.md`](./CONTRIBUTING.md)。要点：

- 只收录有权公开再分发的内容，许可须在[允许范围](./docs/FORMAT.md#许可)内。教辅书、试卷扫描件和商业题库网站的题目不收录。
- PR 必须通过自动校验：数据结构、字段取值、控制字符与乱码、选择题答案与选项是否对应、脚本与内嵌数据、包大小、许可与目录布局等。
- 贡献者需要对照原始资料抽查，并在 PR 中说明剩余的警告。

## 仓库结构

```
banks/
  <来源集>/               同一出处、同一许可的一组题库包
    collection.json       来源、许可、维护者、转换说明
    <包 id>.json          题库包：一个学段、一个学科，最多 5000 题
index.json                应用读取的索引（生成）
docs/
  CATALOG.md              题库目录（生成）
  FORMAT.md               数据格式与校验规则
schema/                   JSON Schema
scripts/qbank.py          打包、规范化、校验、生成索引
tests/                    工具测试
.claude/skills/           题库转换技能
```

题库按来源集分目录：每次贡献只动自己的目录，来源与许可随数据存放，需要下架时可以整目录移除。按学段、学科浏览用 `docs/CATALOG.md` 或 `index.json`，两者都由 `banks/` 生成。

## 数据格式

题库包是 `wrong-notebook-question-bank` v1：

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
    "license": "CC-BY-NC-4.0",
    "updatedAt": "2026-11-11"
  },
  "questions": [
    {
      "id": "cnm_p001_q1",
      "grade": 1,
      "semester": "上",
      "questionType": "fill_blank",
      "difficultyStars": 2,
      "text": "3 的后面一个数是几？",
      "answer": "4",
      "analysis": "从 1 往后数，3 的后面是 4。",
      "knowledgePoints": ["1到5各数的认识"],
      "source": "一年级上册 第1单元 5以内数的认识和加、减法"
    }
  ]
}
```

字段说明、来源集与索引的格式、全部校验规则见 [`docs/FORMAT.md`](./docs/FORMAT.md)。

## 校验

```bash
python3 scripts/qbank.py validate          # 校验整个仓库
python3 -m unittest discover -s tests      # 工具测试
```

## 许可

- 工具、Schema 与文档：MIT，见 [`LICENSE`](./LICENSE)。
- 题库数据：沿用各来源的许可，写在每个来源集的 `collection.json` 中，汇总见 [`docs/CATALOG.md`](./docs/CATALOG.md) 与 [`NOTICE.md`](./NOTICE.md)。部分题库为非商业许可（如 CC-BY-NC-4.0），商业使用前请确认。
- 权利人认为内容不应出现在本仓库的，请开「版权与下架」Issue。
