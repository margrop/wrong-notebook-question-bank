---
name: convert-question-bank
description: 把用户手里的题库（Excel、CSV、Word、PDF、Markdown、JSON、图片等）转换成智能错题本 wrong-notebook 的题库包，校验后交给用户导入应用；用户愿意共享时，再把题库提交到 margrop/wrong-notebook-question-bank 并开 PR。用户提到「转成错题本题库」「导入真题库」「共享题库」「贡献题库」「题库包」或要往本仓库添加题目时使用。
---

# 把题库转换为错题本题库包

产出是一个或多个符合 `wrong-notebook-question-bank` v1 格式的 JSON 文件。用户可以在错题本应用的「真题库」页上传导入；愿意共享的话，再提交到本仓库。

所有打包和校验都通过 `scripts/qbank.py` 完成（Python 3.9+，无第三方依赖）。格式与校验规则的完整说明在 `docs/FORMAT.md`，遇到拿不准的字段或某条校验规则时去读它。

## 开始前

本技能要在 `margrop/wrong-notebook-question-bank` 的克隆目录中运行。当前目录没有 `scripts/qbank.py` 时，先克隆仓库（用户打算共享时克隆其 fork）。

先弄清四件事。能从文件或对话中看出来的就不要问，其余一次问完：

1. **题库在哪、是什么格式。** 先看文件再决定怎么转。
2. **学段与学科。** 学段：`primary` / `junior_high` / `senior_high` / `university`；学科：`math` / `english` / `chinese` / `science` / `physics` / `chemistry` / `biology` / `history` / `geography` / `politics`。一个包只能有一个学段和一个学科，混在一起的题库要拆成多个包。
3. **题目从哪来、版权归谁。** 自编、学校内部资料、公开数据集，还是教辅书或题库网站。
4. **只自己用，还是愿意共享。** 这决定走「只导出」还是「提交 PR」。

## 第 1 步：把题目抽取成中间文件

原始资料和中间文件全部放在仓库的 `.work/` 目录（已被 Git 忽略）。原始资料不能出现在 `banks/` 下，也不能提交。

目标是一个 JSONL 文件，每行一道题：

```json
{"text":"题干","questionType":"single_choice","options":{"A":"…","B":"…"},"answer":"B","analysis":"解析","knowledgePoints":["知识点名"],"grade":7,"semester":"上","difficultyStars":3,"source":"七年级上册 第 2 单元","material":"多题共用的阅读材料"}
```

只有 `text` 和 `questionType` 必填，其余字段原始资料里有才写。字段的含义、取值和长度上限见 `docs/FORMAT.md` 的「题目」一节。

按来源选择抽取方式：

| 来源 | 做法 |
|---|---|
| Excel、CSV | 列名对应字段即可直接交给 `pack`（CSV 支持 `A`、`B`、`C`… 作为选项列，知识点用 `\|` 分隔）；列名不对应时写个小脚本转成 JSONL。Excel 先另存为 CSV，或用 `openpyxl` 读 |
| JSON、其他题库导出 | 写脚本做字段映射 |
| Word | `pandoc -t markdown` 或 `python-docx` 取出文本后再切题。公式要确认转成了 LaTeX，而不是丢失或变成图片 |
| 文本型 PDF | `pdftotext -layout` 取文本后切题。逐页核对公式、上下标和分栏顺序 |
| 扫描件、图片 | 直接看图逐题转写。量大时分批，每批转完就抽查 |
| Markdown、纯文本 | 按题号切题 |

题量大时写脚本批量处理，不要逐题手打。脚本放在 `.work/` 里。

转换时遵守这些规则，它们决定了题目在应用里能不能正常显示和作答：

- **忠实于原文。** 不改写题干，不补写原资料没有的答案或解析。缺答案就不写 `answer`，不要自己解题填上去。发现原资料明显有错时保留原样，并告诉用户。
- **去掉题号。** 题干开头的「1.」「（3）」「第 5 题」属于排版，不属于题目。
- **选择题拆出选项。** 选项放进 `options`，键用 `A`、`B`、`C`…，题干中不再保留选项。`answer` 只写字母，多选写 `AC`。
- **题型用标准取值。** `single_choice` 单选、`multiple_choice` 多选、`true_false` 判断、`fill_blank` 填空、`calculation` 计算、`solution` 解答（含证明、应用、简答）、`reading` 阅读理解、`cloze` 完形填空、`writing` 写作、`other` 其他。`pack` 认识「单选题」「填空题」等常见中文名。
- **公式写成 LaTeX。** 行内 `$…$`，独立成行 `$$…$$`。写 JSON 时反斜杠必须转义成 `\\`（`"$\\frac{1}{2}$"`），否则 `\f`、`\b`、`\t`、`\r`、`\n` 会变成控制字符。用 `json.dumps` 生成 JSON，不要手工拼字符串。
- **共用材料放 `material`。** 阅读理解、题组的每个小题各自成题，材料在每题的 `material` 里重复一份。
- **图片。** 题库包不带图片文件。简单的几何图、函数图、电路图画成 `figureSvg`（一段纯 `<svg>`，不含脚本和外部引用）；画不了的题目不收录，并把跳过的题数和原因告诉用户。不要留下 `![](…)` 或 `<img>`。
- **知识点。** 原资料带知识点或章节信息时写进 `knowledgePoints`。应用按名称把题目和错题的知识点标签匹配起来，名称要与应用内的标签一致，标签数据在 wrong-notebook 仓库的 `src/lib/tags/data/<学科>.ts`（本机若有 `../wrong-notebook` 可直接读）。原资料没有知识点时，问用户是否需要标注；不标注的包仍可导入，只是举一反三无法按知识点从中选题。
- **清掉无关内容。** 水印、网站广告、「版权所有」声明、页眉页脚，以及学生姓名、手机号等个人信息。

## 第 2 步：打包

只自己用，导出到用户指定的位置：

```bash
python3 scripts/qbank.py pack .work/questions.jsonl \
  --out ~/Downloads/my-junior-math.json --id my-junior-math \
  --title "我的初中数学题库" --stage junior_high --subject math \
  --source "自己整理" --license "仅供个人使用"
```

要共享，写入本仓库的来源集目录（见第 5 步的前提）：

```bash
python3 scripts/qbank.py pack .work/questions.jsonl \
  --collection <来源集> --id <来源集>-junior-high-math \
  --title "…" --stage junior_high --subject math \
  --source "…" --source-url "https://…" --license CC-BY-4.0 \
  --maintainer <用户的 GitHub 用户名>
```

`pack` 会整理字段、去掉内容完全相同的题、为没有 `id` 的题生成稳定的 id、在超过 5000 题时自动拆包，并立即运行校验。输入有它修不了的问题（缺题干、题型认不出）时会列出行号并退出，回到第 1 步修正。

包 id 的写法是 `<来源集>-<学段>-<学科>[-<细分>]`，学段用连字符：`primary`、`junior-high`、`senior-high`、`university`。标题要让用户在应用里一眼认出这个题库。

## 第 3 步：校验并修到干净

```bash
python3 scripts/qbank.py validate <文件>      # 只导出时
python3 scripts/qbank.py validate            # 共享时，校验整个仓库
```

- **错误必须全部修掉。** 每条错误的含义和处理办法在 `docs/FORMAT.md` 的「校验规则」。在转换脚本或中间文件里修，然后重新 `pack`，不要手改生成的题库包。
- **警告逐类看。** 用 `--verbose` 看全部。每一类都要有结论：修正了，是误报（如英文题里的 `$5` 触发 `latex-unbalanced`），还是原资料本来如此（如确实没有答案）。只看本次新增的包，仓库里已有包的警告不用管。

## 第 4 步：对照原文抽查

校验脚本查不出抄错的数字和张冠李戴的答案。随机抽至少 20 道题（不足 20 道则全部），与原始资料逐字比对题干、选项、答案、解析；公式多的题和带图的题要多抽。发现系统性的问题（某类公式总是出错、某一页的答案整体错位）就回到第 1 步修转换逻辑，然后重新抽查。

向用户报告：共多少题、各题型多少、跳过了多少题及原因、剩余警告及解释、抽查了多少题和结果。

## 只自己用：交付

告诉用户文件位置和导入方式：打开错题本应用的「真题库」页，选择上传导入。导入的题目默认只进真题库，可以选择同时写入错题本。到这里结束。

## 愿意共享：提交 PR

### 先确认能不能共享

共享意味着公开再分发，以下任何一条不满足就不要提交，向用户说明原因，改为只导出自用：

- 题目是用户自编或用户拥有版权的，或来自以开放许可公开的数据集并能给出链接。教辅书、试卷扫描件、题库网站和 App 里的题目不能收录。
- 许可在允许范围内：`CC0-1.0`、`CC-BY-4.0`、`CC-BY-SA-4.0`、`CC-BY-NC-4.0`、`CC-BY-NC-SA-4.0`、`MIT`、`Apache-2.0`、`BSD-3-Clause`、`PDDL-1.0`、`ODbL-1.0`。第三方数据沿用上游许可；自编题目由用户选择，说明 `CC-BY-4.0`（署名即可使用）和 `CC-BY-NC-4.0`（另加禁止商用）的区别后让用户决定。
- 不含个人信息。

许可和来源由用户说了算，不要替用户编造或猜测。

### 提交

1. 确认在用户 fork 的克隆中（`gh repo fork margrop/wrong-notebook-question-bank --clone` 可一步完成），从最新的 `main` 新建分支，如 `add-<来源集>`。
2. 选来源集 id：小写字母、数字、连字符，能看出出处（如 `myschool`、`openstax`）。先看 `banks/` 下有没有重名。往已有来源集里加包时沿用它的 `collection.json`。
3. 用带 `--collection` 的 `pack` 命令打包（第 2 步）。它会更新 `index.json` 和 `docs/CATALOG.md`。
4. 补全 `banks/<来源集>/collection.json`：`description` 写一两句简介；`notes` 写清转换时做了什么（字段怎么映射、跳过了哪些题、上游有什么使用限制）。改完运行 `python3 scripts/qbank.py format`。
5. 运行 `python3 scripts/qbank.py validate`，结果须为 0 个错误。
6. 用 `git status` 确认改动只有 `banks/<来源集>/`、`index.json`、`docs/CATALOG.md`，然后提交。提交信息用简体中文，如 `feat: 新增某校初中数学题库（1200 题）`。
7. **推送和开 PR 之前先征得用户同意**：给用户看包的清单、题数、许可和 PR 描述草稿。同意后推送，并用 `gh pr create` 开 PR。PR 描述按 `.github/PULL_REQUEST_TEMPLATE.md` 填写，如实写明来源、许可、剩余警告的解释和抽查结果。
8. 把 PR 链接给用户。CI 失败时读日志，修正后追加提交。

修改已有的包（纠错、补题）时，保留原有题目的 `id`，更新 `meta.updatedAt`，然后 `format`、`build`、`validate`。
