# 数据来源与许可

本仓库只做结构化打包，题目、答案、解析与知识点名称来自下列公开项目。打包不改变题目内容。

## cn-math-taxonomy

- 仓库：https://github.com/xiaoyang111222/cn-math-taxonomy
- 许可：CC BY-NC 4.0（https://creativecommons.org/licenses/by-nc/4.0/）
- 使用范围：`taxonomy-*` 全部题库包
- 获取日期：2026-11-11（`data/topics.json`、`data/questions.json`）
- 转换：按题目 `topicId` 关联知识点 `name`、`grade`、`semester`、`chapter`；`morality` 学科记为 `politics`；高中 13–16 册次统一记为 `grade: 12`。
- 上游说明：知识图谱与题库仍需一线教师审核；商业使用需单独授权。

## rainewhk/gaokao

- 仓库：https://github.com/rainewhk/gaokao
- 许可：Apache-2.0
- 上游来源：GAOKAO-Bench（https://github.com/OpenLMLab/GAOKAO-Bench）、GAOKAO-Bench-Updates
- 使用范围：`gaokao-senior-high-*` 全部题库包
- 获取日期：2026-11-11
- 转换：按目录学科、年份、卷别与题型拆分；答案数组转为逗号分隔文本；保留题干 LaTeX 与解析。
- 上游说明：题目版权归原出题机构；不保证答案与解析完全准确；仅供研究学习。

## 本仓库结构

索引格式、JSON Schema 与校验脚本为 MIT 许可。题库数据沿用上述来源许可；再分发时请保留本文件与来源链接。
