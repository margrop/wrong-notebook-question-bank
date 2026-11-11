# 贡献指南

欢迎共享题库、修正题目和改进工具。提交前请读完本文；格式细节见 [`docs/FORMAT.md`](./docs/FORMAT.md)。

## 共享题库

### 能收录什么

- 你自编的题目，或你拥有版权并愿意以开放许可发布的题目。
- 他人以开放许可公开的数据集，许可须在[允许范围](./docs/FORMAT.md#许可)内，并能给出来源链接。

不能收录：教辅书、试卷扫描件、商业题库网站或 App 里的题目；没有声明许可的网络资料；含学生姓名、成绩、联系方式等个人信息的内容。拿不准时先开 Issue 问。

### 步骤

用 AI 编程助手（Claude Code、Codex、Cursor 等）的话，在本仓库目录中让它「把我的题库转成错题本题库格式」，它会按 [`.claude/skills/convert-question-bank/SKILL.md`](./.claude/skills/convert-question-bank/SKILL.md) 完成下面的全部步骤。手工操作如下：

1. Fork 本仓库并新建分支。
2. 把题目整理成 CSV、JSONL 或 JSON 数组，一题一条，字段名见 [`docs/FORMAT.md`](./docs/FORMAT.md#题目)。原始资料和中间文件放在 `.work/`（已被 Git 忽略），不要提交。
3. 打包。下面的命令会写入 `banks/<来源集>/`，首次使用某个来源集时创建 `collection.json`，并更新索引：

   ```bash
   python3 scripts/qbank.py pack .work/questions.jsonl \
     --collection myschool --id myschool-junior-high-math \
     --title "某校初中数学练习" --stage junior_high --subject math \
     --source "某校数学组自编" --license CC-BY-4.0 --maintainer 你的GitHub用户名
   ```

4. 补全 `banks/<来源集>/collection.json` 里的 `description` 和 `notes`。
5. 校验，直到没有错误，并逐类处理警告：

   ```bash
   python3 scripts/qbank.py validate
   ```

6. 抽查：随机抽至少 20 道题（不足 20 道则全部），与原始资料逐字比对题干、选项、答案和解析。
7. 提交并开 PR，按模板填写。一个 PR 只涉及一个来源集。

### PR 要求

自动检查（必须通过）：

- `python3 scripts/qbank.py validate` 没有错误：数据结构、字段取值、题数、包大小、控制字符、脚本与内嵌数据、选择题答案与选项是否对应、许可、目录布局等，完整清单见[校验规则](./docs/FORMAT.md#校验规则)。
- `index.json` 与 `docs/CATALOG.md` 已用 `python3 scripts/qbank.py build` 更新。
- 题库包与 JSON Schema 一致，工具测试通过。

CI 用两套规则校验 PR 中的数据：PR 自带的校验脚本，以及主分支上的校验脚本。因此不能靠修改校验脚本让数据通过。

人工审阅（维护者会看）：

- 来源与许可真实、可核对。
- 警告已逐类说明：哪些是误报，哪些是原始资料如此，哪些已修正。CI 会在运行摘要中单独列出本次改动的题库包的警告。
- 抽查结果：抽了多少题，发现并修正了什么。
- diff 中没有与本次贡献无关的改动。

## 修正题目

发现题目、答案或解析有误，可以开「题目纠错」Issue，或直接提 PR 修改对应的行。修改时保留题目 `id`，更新该包 `meta.updatedAt`，然后运行 `format`、`build`、`validate`。第三方来源的题目有误时，也请向上游反馈。

## 下架

权利人认为某些内容不应出现在本仓库的，请开「版权与下架」Issue，说明涉及的来源集或题目以及权利依据。维护者核实后移除。

## 修改工具与格式

- 改动 `scripts/qbank.py` 时同步更新 `tests/`、`schema/` 与 `docs/FORMAT.md`，并运行 `python3 -m unittest discover -s tests`。
- 工具只用 Python 3.9+ 标准库，不引入第三方依赖（测试中的 JSON Schema 校验可选依赖 `jsonschema`）。
- 新增校验规则前，先在现有数据上跑一遍：现有数据触发的错误要在同一个 PR 中修好。
- 题库格式由应用 [wrong-notebook](https://github.com/margrop/wrong-notebook) 的 `src/lib/question-bank/format.ts` 决定。格式变更须先在应用端支持，见 [`docs/FORMAT.md`](./docs/FORMAT.md#格式变更)。

## 许可

提交到本仓库的工具代码与文档以 MIT 许可发布；题库数据以各来源集 `collection.json` 中声明的许可发布。提交 PR 即表示你确认有权以该许可发布这些内容。
