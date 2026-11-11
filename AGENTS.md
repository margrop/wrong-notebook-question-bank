# AGENTS.md

本文件为在本仓库工作的 AI 代理（Claude Code、Codex、Cursor 等）提供约定。

## 项目概览

本仓库是智能错题本 [margrop/wrong-notebook](https://github.com/margrop/wrong-notebook) 的共享题库下载仓库。应用的「真题库」页通过 jsDelivr 读取 `main` 分支的 `index.json`，再按其中的 `file` 路径下载题库包。合并到 `main` 的内容会直接到达用户，所以 `main` 上的数据必须始终通过校验。

仓库里只有数据、一个 Python 工具和文档，没有需要构建或部署的程序。

## 目录结构

| 路径 | 说明 |
| --- | --- |
| `banks/<来源集>/` | 一个来源集：`collection.json`（来源、许可、维护者）和若干题库包 `<包 id>.json` |
| `index.json` | 应用读取的索引。**生成文件**，由 `qbank.py build` 写出 |
| `docs/CATALOG.md` | 题库目录。**生成文件** |
| `docs/FORMAT.md` | 题库包、来源集、索引的格式，以及全部校验规则 |
| `schema/` | 三种数据文件的 JSON Schema |
| `scripts/qbank.py` | 唯一的工具：`pack` / `format` / `validate` / `build` |
| `tests/` | 工具的单元测试，以及对仓库现有数据的校验 |
| `.claude/skills/convert-question-bank/` | 把用户题库转换为题库包并提交 PR 的技能 |
| `.github/` | CI、PR 模板、Issue 模板 |
| `.work/` | 转换时的原始资料与中间文件，已被 Git 忽略 |

## 常用命令

```bash
python3 scripts/qbank.py validate            # 校验整个仓库；加 --quiet 只看错误
python3 scripts/qbank.py validate <文件>      # 校验单个题库包
python3 scripts/qbank.py format              # 把 banks/ 下的文件改写为规范格式
python3 scripts/qbank.py build               # 重新生成 index.json 与 docs/CATALOG.md
python3 scripts/qbank.py pack --help         # 把 CSV / JSONL / JSON 打包为题库包
python3 -m unittest discover -s tests        # 测试
```

提交前必须通过：`python3 scripts/qbank.py validate` 无错误，`python3 -m unittest discover -s tests` 通过。

## 任务指引

- **转换用户的题库、新增题库包、提交共享题库的 PR**：按 [`.claude/skills/convert-question-bank/SKILL.md`](./.claude/skills/convert-question-bank/SKILL.md) 执行。不支持技能的代理直接阅读该文件并照做。
- **修正题目**：直接改题库包里对应的行，保留题目 `id`，更新该包的 `meta.updatedAt`，然后依次运行 `format`、`build`、`validate`。
- **修改工具、格式或校验规则**：见下方「工具与格式」。

## 数据约定

- 不手工编辑 `index.json` 和 `docs/CATALOG.md`，改完数据运行 `build`。
- 不手工调整题库包的排版，运行 `format`。规范排版是每题一行，PR 可以逐题 diff。
- 一个包只含一个学段、一个学科；单包不超过 5000 题、5 MB；全仓库不超过 500 个包。超出时拆包，不要放宽上限，这些上限来自应用端。
- 包 id 为 `<来源集>-<学段>-<学科>[-<细分>]`，学段写作 `primary` / `junior-high` / `senior-high` / `university`。已发布的包 id 和题目 id 不改名。
- 原始资料（Word、PDF、图片、表格）和转换脚本的中间产物放在 `.work/`，不提交。`banks/` 下只允许 `collection.json` 和题库包。
- 不凭空生成题目、答案或解析来充实题库。转换时忠实于原始资料，缺失的字段留空。
- 新增来源集前确认许可在 [`docs/FORMAT.md`](./docs/FORMAT.md#许可) 的允许范围内，来源可核对。教辅书、试卷扫描件、商业题库网站的内容不收录。
- 不用降低校验等级、增加豁免名单的方式让数据通过。数据触发错误时修数据；规则确实有误时修规则，并补测试。

## 工具与格式

- `scripts/qbank.py` 只用 Python 3.9+ 标准库，保持单文件，方便 CI 用主分支的版本校验 PR 的数据。不使用 3.10 以上才有的语法（`match`、`X | Y` 类型注解）。
- 校验规则、JSON Schema、`docs/FORMAT.md` 三者要一致。改其中之一时同步另外两处，并在 `tests/test_qbank.py` 中增加用例。
- 新增或收紧校验规则前，先对现有数据运行。现有数据触发的错误在同一次改动中修好，并把对上游数据的修正记入该来源集 `collection.json` 的 `notes`。
- 题库格式由应用端 `src/lib/question-bank/format.ts`（wrong-notebook 仓库）决定，那里的字段名、长度上限、题数上限是事实来源。应用端解析时会丢弃未知字段，所以本仓库的校验拒绝未知字段，避免拼写错误被静默吞掉。
- 应用的默认索引地址是 `https://cdn.jsdelivr.net/gh/margrop/wrong-notebook-question-bank@main/index.json`，包地址为索引所在目录加 `file`。不要移动 `index.json`，不要改变 `file` 相对仓库根的语义。

## 语言

回复、文档、代码注释和 commit message 使用简体中文。commit message 采用 `feat:` / `fix:` / `docs:` / `chore:` 前缀。

## 安全

- 题库内容会在应用中渲染。`figureSvg` 和文本字段不得含脚本、事件属性、外部引用或内嵌的 base64 数据，校验会拒绝这些内容，不要绕过。
- CI 只需要只读权限。不要给工作流增加写权限或密钥，不要使用 `pull_request_target`。
- 不提交个人信息（学生姓名、成绩、手机号等）。
