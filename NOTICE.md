# 数据来源与许可

本仓库包含第三方公开题库的结构化打包，以及维护者提供的自编、AI 辅助新编题库。第三方题目、答案、解析与知识点名称按各来源标注权利归属；自编来源的生成方式、审核说明和许可单独记录。

每个来源集的出处、许可、获取日期和转换说明记录在 `banks/<来源集>/collection.json`，汇总表见 [`docs/CATALOG.md`](./docs/CATALOG.md)。再分发题库数据时，请保留对应的 `collection.json` 和来源链接，并遵守该来源的许可。

## 需要特别注意的来源

- **`ai-math-thinking`**（[来源说明](./banks/ai-math-thinking/collection.json)，[CC-BY-NC-4.0](https://creativecommons.org/licenses/by-nc/4.0/)）：由维护者 `margrop` 提供的 AI 辅助独立新编数学练习，使用时须署名并限非商业用途。公开包包含新题、答案、解析和知识点；参考资料的原题文字、原图与私有审核中间文件不随题库发布。题目经过多模型审题、独立程序复算和 AI 执行代理复核。
- **`taxonomy`**（[xiaoyang111222/cn-math-taxonomy](https://github.com/xiaoyang111222/cn-math-taxonomy)，CC-BY-NC-4.0）：仅限非商业使用，商业使用需向原作者单独授权。上游说明其知识图谱与题库仍需一线教师审核。
- **`gaokao`**（[rainewhk/gaokao](https://github.com/rainewhk/gaokao)，Apache-2.0，整合 [GAOKAO-Bench](https://github.com/OpenLMLab/GAOKAO-Bench) 与 GAOKAO-Bench-Updates）：数据集以 Apache-2.0 发布，题目版权归原出题机构；上游说明不保证答案与解析完全准确，仅供研究学习。

## 本仓库自身

索引格式、JSON Schema、工具脚本与文档以 MIT 许可发布，见 [`LICENSE`](./LICENSE)。

## 下架

权利人认为某些内容不应出现在本仓库的，请开「版权与下架」Issue，维护者核实后移除。
