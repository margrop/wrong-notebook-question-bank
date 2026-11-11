# 题库格式与校验规则

本仓库有三种数据文件：

| 文件 | 位置 | 谁来写 | JSON Schema |
|---|---|---|---|
| 题库包 | `banks/<来源集>/<包 id>.json` | 贡献者（用 `qbank.py pack` 生成） | [`question-bank.schema.json`](../schema/question-bank.schema.json) |
| 来源集说明 | `banks/<来源集>/collection.json` | 贡献者 | [`collection.schema.json`](../schema/collection.schema.json) |
| 索引 | `index.json` | `qbank.py build` 生成，不手工修改 | [`index.schema.json`](../schema/index.schema.json) |

应用读取 `index.json`，再按其中的 `file` 下载题库包。应用端的解析代码在 wrong-notebook 的 `src/lib/question-bank/format.ts`，本文的长度上限与它保持一致。

## 来源集

一个来源集是同一出处、同一许可的一组题库包，占 `banks/` 下的一个目录。一次贡献通常只新增或修改一个来源集目录，互不影响；需要下架时也可以整目录移除。

```json
{
  "id": "gaokao",
  "title": "高考真题汇编（2010–2024）",
  "description": "历年高考真题，含答案与解析；题目未标知识点。",
  "origin": "third_party",
  "source": "rainewhk/gaokao",
  "sourceUrl": "https://github.com/rainewhk/gaokao",
  "license": "Apache-2.0",
  "obtainedAt": "2026-11-11",
  "maintainers": ["margrop"],
  "notes": "转换时做了什么：字段如何映射、改了哪些内容、上游有哪些使用限制。"
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 小写字母、数字、连字符，最长 40 字，与目录名相同 |
| `title` | 是 | 来源集名称 |
| `description` | 否 | 一两句话的简介 |
| `origin` | 是 | `third_party`：整理自他人公开的数据；`original`：贡献者自编或拥有版权 |
| `source` | 是 | 来源名称 |
| `sourceUrl` | `third_party` 必填 | 来源链接 |
| `license` | 是 | 见下方「许可」 |
| `obtainedAt` | 否 | 获取上游数据的日期，`YYYY-MM-DD` |
| `maintainers` | 是 | 至少一个 GitHub 用户名（不带 `@`），题目有误时找这些人 |
| `notes` | 否 | 转换说明与上游的使用限制 |

### 许可

`license` 只接受允许再分发并允许改编的许可（格式转换属于改编）：

`CC0-1.0`、`CC-BY-4.0`、`CC-BY-SA-4.0`、`CC-BY-NC-4.0`、`CC-BY-NC-SA-4.0`、`MIT`、`Apache-2.0`、`BSD-3-Clause`、`PDDL-1.0`、`ODbL-1.0`

带 ND（禁止演绎）条款的许可、未声明许可的资料、教辅书和商业题库网站的内容不能收录。其他开放许可请先开 Issue 讨论。自编题目建议用 `CC-BY-4.0` 或 `CC-BY-NC-4.0`。

## 题库包

```json
{"format":"wrong-notebook-question-bank","version":1,
"meta":{"id":"taxonomy-primary-math","title":"数学题库（小学）","stage":"primary","subject":"math","grades":[1,2,3,4,5,6],"count":1136,"tagged":true,"source":"cn-math-taxonomy","sourceUrl":"https://github.com/xiaoyang111222/cn-math-taxonomy","license":"CC-BY-NC-4.0","updatedAt":"2026-11-11"},
"questions":[
{"id":"cnm_p001_q1","grade":1,"semester":"上","questionType":"fill_blank","difficultyStars":2,"text":"3 的后面一个数是几？","answer":"4","analysis":"从 1 往后数，3 的后面是 4。","knowledgePoints":["1到5各数的认识"],"source":"一年级上册 第1单元 5以内数的认识和加、减法"},
{"id":"cnm_p001_q2","grade":1,"semester":"上","questionType":"single_choice","text":"下面哪个数最大？","options":{"A":"2","B":"5","C":"3"},"answer":"B"}
]}
```

文件为无 BOM 的 UTF-8，固定排版：头部一行、`meta` 一行、每题一行。这样 PR 里能逐题看 diff。排版由 `python3 scripts/qbank.py format` 完成，不需要手工对齐。

### 包的划分与命名

- 一个包只含一个学段、一个学科。
- 包 id 为 `<来源集>-<学段>-<学科>[-<细分>]`，学段写作 `primary` / `junior-high` / `senior-high` / `university`，例如 `gaokao-senior-high-math`。文件名为 `<包 id>.json`。校验只强制「以来源集 id 开头」和「与文件名一致」。
- 单包最多 5000 题、5 MB。超出时按年级、年份或册次拆分并写进 id（如 `…-math-g7`、`…-math-2024`）；`pack` 在超过 5000 题时会自动拆成 `-p1`、`-p2`。
- 包 id 发布后不要改名；题目 `id` 发布后保持稳定，修订题目时沿用原 id。
- 全仓库最多 500 个包（应用索引上限）。

### meta

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 包 id，见上 |
| `title` | 是 | 应用中显示的题库名，最长 200 字。应用按名称区分已导入的题库，标题要能与其他包区分开 |
| `description` | 否 | 最长 1000 字 |
| `stage` | 是 | `primary` / `junior_high` / `senior_high` / `university` |
| `subject` | 是 | `math` / `english` / `chinese` / `science` / `physics` / `chemistry` / `biology` / `history` / `geography` / `politics` |
| `grades` | 是 | 包内出现的年级，升序数组，可为空 |
| `count` | 是 | 题数，须与 `questions` 长度一致 |
| `tagged` | 是 | 是否带知识点。为 `true` 时举一反三才能按知识点从本包选题 |
| `source` | 是 | 来源名称 |
| `sourceUrl` | 否 | 来源链接 |
| `license` | 是 | 须与 `collection.json` 的 `license` 相同 |
| `updatedAt` | 是 | 本包最后修改日期，`YYYY-MM-DD` |

### 题目

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 包内唯一、稳定的题号，最长 200 字 |
| `text` | 是 | 题干，最长 20000 字。公式用 `$…$` / `$$…$$` 包裹的 LaTeX，可用 Markdown |
| `questionType` | 是 | `single_choice` 单选、`multiple_choice` 多选、`true_false` 判断、`fill_blank` 填空、`calculation` 计算、`solution` 解答、`reading` 阅读理解、`cloze` 完形填空、`writing` 写作、`other` 其他 |
| `options` | 否 | 选项对象 `{"A":"…","B":"…"}`，键用单个大写字母；选择题应把选项从题干中拆出来 |
| `answer` | 否 | 答案，最长 20000 字。选择题写选项字母，多选写 `AC` 或 `A,C` |
| `analysis` | 否 | 解析，最长 50000 字 |
| `material` | 否 | 多题共用的阅读材料或题组背景，最长 20000 字 |
| `knowledgePoints` | 否 | 知识点名称数组，最多 100 个、每个最长 200 字。应用按名称与错题的知识点标签匹配，名称应与应用内的标签一致（见 wrong-notebook 的 `src/lib/tags/data/`） |
| `grade` | 否 | 1–6 小学，7–9 初中，10–12 高中；高中选择性必修统一记 12 |
| `semester` | 否 | `上` / `下` / `全`（全一册） |
| `difficultyStars` | 否 | 1–5 的整数 |
| `source` | 否 | 出处，如「2023 年全国甲卷 第 5 题」「七年级上册 第 2 单元」，最长 200 字 |
| `figureSvg` | 否 | 配图，一段 `<svg>` 文本，最大 200 KB |
| `stage` / `subjectKey` | 否 | 与 `meta` 不同时才需要写 |

可选字段没有值时直接省略，也可写 `null`。不认识的字段会被校验拒绝，以免拼写错误的字段被应用静默丢弃。

题库包不携带图片文件。题目依赖图片时，把图画成 `figureSvg`；做不到就不要收录这道题，或在题干中用文字把图描述清楚。

## 索引

`index.json` 由 `python3 scripts/qbank.py build` 根据 `banks/` 生成，同时生成 [`docs/CATALOG.md`](./CATALOG.md)。`packages` 的每一项是包的 `meta` 加上 `collection`、`file`（相对仓库根的路径）、`sizeBytes`、`sha256`，按学段、学科、包 id 排序。

## 校验规则

```bash
python3 scripts/qbank.py validate            # 整个仓库
python3 scripts/qbank.py validate 某个包.json  # 单个文件
```

错误（ERROR）会让校验失败，PR 无法合并；警告（WARN）不阻断，但贡献者要在 PR 中逐类说明。`--strict` 把警告也当作失败，`--verbose` 列出全部问题，`--quiet` 只列错误。

### 错误

| 规则 | 含义 | 处理 |
|---|---|---|
| `json` / `encoding` / `format` | 不是无 BOM 的 UTF-8 JSON，或 `format`、`version` 不对 | 用 `pack` 重新生成 |
| `not-canonical` | 排版不是规范格式 | `python3 scripts/qbank.py format` |
| `stale-generated` | `index.json` 或 `docs/CATALOG.md` 与题库内容不一致 | `python3 scripts/qbank.py build` |
| `layout` | `banks/` 下有不该出现的文件（原始资料、图片等）或空目录 | 移走；原始资料不入库 |
| `collection` / `license` | `collection.json` 缺字段、取值无效，许可不在允许范围，或包的许可与来源集不一致 | 按上文修正 |
| `package-id` | 包 id 格式不对、与文件名不符、不以来源集 id 开头，或与其他包重复 | 改 id 或文件名 |
| `meta` / `question-count` | `meta` 缺字段或取值无效；题数为 0、超过 5000，或与 `count` 不符 | 修正；超限拆包 |
| `file-too-large` | 包超过 5 MB | 拆包 |
| `unknown-field` | 出现未定义的字段 | 多为拼写错误，如 `subject` 应为 `subjectKey` |
| `field-type` / `field-empty` / `field-too-long` / `enum` | 字段类型、取值或长度不合规 | 按字段表修正 |
| `duplicate-id` / `id-format` | 包内题目 id 重复，或首尾有空白 | 改 id |
| `knowledge-point` | 知识点为空、重复、过长或首尾有空白 | 清理 |
| `options` | 只有一个选项 | 多为选项拆分出错 |
| `answer-not-in-options` | 选择题答案的字母不在选项里 | 核对原题 |
| `control-char` | 含控制字符或替换字符 `U+FFFD`。常见原因是 LaTeX 反斜杠没转义：`\frac` 变成换页符、`\bar` 变成退格符、`\right` 变成回车 | 修正转换脚本，从原始资料重新生成 |
| `active-content` | 含 `<script>`、`<iframe>`、`javascript:` 等 | 删除 |
| `embedded-data` | 含 base64 内嵌数据 | 配图改用 `figureSvg` |
| `figure-svg` | `figureSvg` 不是 SVG，超过 200 KB，或含脚本、事件属性、外部引用 | 只保留纯图形元素 |

### 警告

| 规则 | 含义 |
|---|---|
| `answer-missing` | 没有答案，或答案是「略」「见解析」之类的占位 |
| `choice-no-options` | 选择题没有单列 `options`，选项还在题干里 |
| `single-choice-multi-answer` | 单选题的答案有多个字母，题型可能应为多选 |
| `option-keys` | 选项键不是单个大写字母 |
| `duplicate-question` | 包内有题干、材料、选项完全相同的题 |
| `grade-out-of-stage` | 年级不在学段范围内 |
| `text-too-short` | 题干不足 2 个字 |
| `latex-unbalanced` | `$` 数量为奇数，公式可能没闭合（货币符号会误报） |
| `latex-escape` | 疑似 `\times`、`\neq` 等丢了反斜杠，变成制表符或换行 |
| `mojibake` | 疑似乱码（「锟斤拷」、`Ã©` 等） |
| `private-use-char` | 含私用区字符，多来自 Word、PDF 的公式字体，显示为方块 |
| `external-image` | 题干引用了图片（`![]()`、`<img>`），应用里看不到 |
| `pii` | 疑似手机号或身份证号 |
| `promo` | 疑似水印、广告或版权声明（「公众号」「版权所有」等） |
| `meta-tagged` | 所有题目都带知识点，`tagged` 却是 `false` |

机器校验查不出答案对错、题干与原题是否一致。这部分靠贡献者抽查和维护者审阅，要求见 [`CONTRIBUTING.md`](../CONTRIBUTING.md)。

## 格式变更

`version` 目前为 1。新增可选字段不升版本，但要先确认应用端会忽略或已支持该字段；删除字段、改变字段含义或取值范围需要升版本，并与应用端同步发布。改动格式时同步修改 `scripts/qbank.py`、`schema/`、本文和 `tests/`。
