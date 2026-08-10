# Agent 目录

`.agents/` 存放面向 Agent 的能力和本论文项目约定。

## Active Skill 规则

只有匹配以下模式的目录才是 active project Skills：

```text
.agents/skills/<skill-name>/SKILL.md
```

仓库中的其他文件夹可能包含导入示例、供应商归档或历史 `SKILL.md` 文件，但除非复制到 `.agents/skills/`，否则不会被视为本项目 active Skill。

## 职责

- `.agents/skills/` 存放 Agent 可以使用的能力。
- `route-map.yml` 决定某个任务应使用哪个 Skill 或 workflow。
- `workflows/` 描述多个 Skill 如何在论文流程中协作。

不要在这里存放论文证据、实验结果、数据或章节草稿。
