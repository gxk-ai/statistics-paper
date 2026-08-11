---
name: documentation-system
description: Organize, place, and migrate repository documentation using the repo's documentation system. Use when creating new docs, restructuring docs directories, deciding where RFC/ADR/SPEC/protocol/user docs should live, or checking whether a change is blocked on missing design documents.
---

# Documentation system

## Goal

用仓库统一的文档系统放置、迁移与治理文档，而不是随意新增页面或堆叠重复说明。

默认参考：

- `docs/developers/playbooks/documentation-system.md`
- `docs/README.md`
- `docs/developers/README.md`
- `docs/internal/README.md`
- `docs/users/README.md`
- `AGENTS.md`

## 何时使用

当任务涉及以下内容时，优先使用本 skill：

- 新建设计文档、协议文档、实现说明或用户文档
- 重构 `docs/` 目录
- 判断现有文档该迁到哪里
- 判断当前变更是否缺少前置设计材料
- 决定某份文档该放在 `users`、`developers`、`internal` 的哪一层

## Workflow

1. 先判断受众
   - 最终用户 -> `docs/users/`
   - 开发者 / 集成者 -> `docs/developers/`
   - 维护者 / 系统设计者 -> `docs/internal/`
2. 再判断材料职责
   - 流程 / 工作手册 -> `playbooks/`
   - how-to / 操作指导 -> `guides/` 或 `how-to/`
   - 参考资料 -> `references/` 或 `reference/`
   - 方案讨论 -> `rfcs/`
   - 最终决策 -> `adrs/`
   - 非协议型规范 -> `specs/`
   - 协议真相源 -> `protocols/`
   - 原则与不变量 -> `principles/`
   - 实现方案 / 迁移说明 -> `implementation/`
3. 检查真相源
   - 同一主题只能有一个主真相源
   - 其他文档应引用，不应复制整段内容
4. 检查前置门槛
   - repo-level / cross-cutting / protocol 级变更，先确认是否已有对应设计材料
   - 缺少前置文档时，先补文档，再进入实现
5. 做迁移时的默认策略
   - 优先通过 `mv` 做物理归类
   - 先修入口与高价值链接
   - 不把目录迁移变成全文重写工程

## 默认放置规则

- `docs/developers/playbooks/`：治理手册、工作流、交付流程
- `docs/developers/guides/`：开发 how-to
- `docs/developers/references/`：开发参考材料
- `docs/users/tutorials/`：入门
- `docs/users/how-to/`：常见操作
- `docs/users/explanations/`：概念解释
- `docs/users/reference/`：FAQ 与参考项
- `docs/internal/protocols/`：协议类真相源
- `docs/internal/specs/`：非协议型规范与规则

## 完成标准

- 文档放在正确的受众层与材料层
- repo-level / cross-cutting 变更满足前置门槛
- 迁移优先体现结构清晰，而不是追求一次性内容完美
- 入口页与 README 能帮助团队快速找到文档
