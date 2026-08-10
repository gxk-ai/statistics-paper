# 27lunwen

这是一个面向毕业论文长期推进的项目工作区。它的目标不是只保存论文正文，而是系统保存研究上下文、文献证据、算法代码、实验记录、论文草稿和 Agent 工作流，避免项目中断一段时间后忘记之前做到了哪里、为什么这样做、结果从哪里来。

## 从这里开始

每次重新开始这个项目时，先按顺序阅读：

1. `START_HERE.md`
2. `project-state.yml`
3. `thesis-map.yml`
4. `route-map.yml`

这几个文件分别回答：

- 当前论文推进到什么阶段？
- 下一步应该做什么？
- 哪些结论、图表、实验和文献已经进入论文证据链？
- 当前任务应该使用哪个 Skill 或 workflow？

## 项目结构

```text
27lunwen/
|-- .agents/
|   `-- skills/
|-- workflows/
|-- research/
|-- references/
|-- data/
|-- src/
|-- experiments/
|-- artifacts/
|-- thesis/
|-- templates/
|-- config/
|-- START_HERE.md
|-- project-state.yml
|-- thesis-map.yml
|-- route-map.yml
`-- FRAMEWORK_REVIEW.md
```

## 目录职责

| 路径 | 职责 |
| --- | --- |
| `.agents/skills/` | 项目的 active Skill 能力库。只有 `.agents/skills/<skill-name>/SKILL.md` 会被视为本项目可触发 Skill。 |
| `workflows/` | 多步骤论文任务流程，说明多个 Skill、文件和产物如何协作。 |
| `research/` | 研究记忆层：研究问题、假设、变量、方法、决策记录、发现和工作日志。 |
| `references/` | 文献资产：检索日志、文献矩阵、BibTeX、阅读笔记。 |
| `data/` | 数据资产：原始数据、中间数据、处理后数据、外部数据和数据说明。 |
| `src/` | 可复用的算法、建模和分析代码。 |
| `experiments/` | 实验配置、notebook、运行日志、指标和可复现记录。 |
| `artifacts/` | 可进入论文或答辩的生成物：图、表、报告、模型产物。 |
| `thesis/` | 论文正文草稿和最终稿。 |
| `templates/` | 可复用模板：章节模板、decision record、finding、三线表、导出模板等。 |
| `config/` | 项目级配置，例如路径、随机种子、格式要求、数据切分策略等。 |

## 算法代码放置规则

如果论文里有较多算法代码，使用下面的分层：

```text
src/           可复用代码
experiments/   具体实验、配置、notebook、运行记录
data/          数据和数据说明
artifacts/     论文可用的图表、模型、报告
thesis/        论文正文
```

可复用代码放在 `src/`：

```text
src/
|-- data/
|-- features/
|-- models/
|-- training/
|-- evaluation/
|-- visualization/
`-- utils/
```

每一次重要实验单独放入：

```text
experiments/runs/EXP-XXX/
|-- config.yaml
|-- run.log
|-- metrics.json
|-- environment.txt
`-- outputs/
```

判断标准：

- 会被多次复用的代码，放 `src/`。
- 某一次实验的配置、日志和结果，放 `experiments/`。
- 论文最终采用的图表、模型、报告，放 `artifacts/`。
- 原始数据和处理后数据，放 `data/`。
- 进入论文正文的文字，放 `thesis/`。

## 长期记忆规则

每次完成一段实质性工作后，至少更新：

1. `project-state.yml`
2. `research/logs/`
3. 必要时更新 `research/decisions/`
4. 必要时更新 `research/findings/`
5. 如果新增了重要结论、图、表或实验结果，更新 `thesis-map.yml`

这是防止项目中断后失忆的核心机制。

## 路由规则

使用 `route-map.yml` 判断当前任务应该交给哪个 Skill 或 workflow。

常见任务路由：

- 文献综述：`literature-review` + `citation-management`
- 研究设计：`scientific-brainstorming` + `scientific-critical-thinking`
- 论文写作：`scientific-writing` + `stat-writing`
- 图表和机制图：`scientific-visualization` + `scientific-schematics`
- 排版和导出：`latex-typesetting`、`md-to-docx`、`docx-to-md`
- 算法和实验：`src/`、`experiments/`、`data/`、`artifacts/`

## 证据追踪规则

不要把一个重要结论直接写进 `thesis/`，除非它能追溯到至少一个来源：

- `references/literature-matrix.xlsx`
- `references/notes/`
- `research/findings/`
- `experiments/runs/`
- `artifacts/`
- `thesis-map.yml`

论文正文要可读，项目本身也要可审计、可恢复、可复现。

## 框架审查结论

项目框架审查记录见 `FRAMEWORK_REVIEW.md`。

结论：这个框架适合长期毕业论文项目，也适合包含较多算法代码的后续开发。前提是每次阶段性工作结束后，持续维护 `project-state.yml` 和 `thesis-map.yml`。
