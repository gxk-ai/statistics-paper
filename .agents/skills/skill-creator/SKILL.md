---
name: skill-creator
description: Author, evaluate, and iterate MODELEX skills — turning a repeated workflow, domain knowledge, or output convention into a triggerable, maintainable SKILL.md. Use when the user asks to create, update, benchmark, or improve a skill, write test prompts for one, or fix a skill that "won't trigger". Do NOT use to invoke an existing skill for its own task (use skill.load) or for non-skill files. Key rule: when triggering is the complaint, fix the front-matter description first — it is the only part the model sees when deciding to fire.
---

# Skill Creator

用于创建、评估和迭代 MODELEX skills。工作目标是把用户的领域知识、固定流程、工具用法或输出规范沉淀成一个可触发、可维护、可验证的 `SKILL.md`。

## 使用方式

根据用户所在阶段切入：

- 用户只有想法：先澄清意图，再起草 skill。
- 用户已有草稿：先审查结构、触发描述和资源组织，再小步修改。
- 用户担心效果：设计测试提示词和评估标准，再根据结果迭代。
- 用户说“很难触发”：优先优化 front matter 的 `description`。

除非用户明确只要讨论，否则在信息足够时直接修改或创建文件。

## 创建流程

1. 捕获意图：
   - skill 要让 MODELEX 做什么？
   - 什么用户请求、文件类型、工具场景或关键词应该触发它？
   - 期望输出格式是什么？
   - 是否需要 bundled resources（`references/`、`scripts/`、`assets/`、`agents/`）？
2. 起草 `SKILL.md`：
   - front matter 必须包含 `name` 和 `description`。
   - 正文只保留执行工作流所需的核心说明。
   - 细节材料放入同目录资源文件，并在正文中说明何时读取。
3. 设计 2-5 条真实测试提示词：
   - 覆盖正常路径、边界情况和不应触发的场景。
   - 对可验证任务写出明确 expectations。
4. 运行或模拟评估：
   - 对每条提示词记录是否触发、是否遵循流程、是否达成输出。
   - 如果可以启动子代理，可用子代理独立检查草稿或评估结果。
5. 迭代：
   - 每次只改一个主要问题。
   - 修改后重新检查 `description`、正文和资源链接是否一致。

## `SKILL.md` 契约

每个 skill 目录至少包含：

```text
skill-id/
├── SKILL.md
└── references/   可选，按需读取的长文档
```

`SKILL.md` 最小模板：

```md
---
name: <skill-id>
description: <做什么 + 何时使用>
---

# <Title>

## Workflow

...
```

要求：

- `name` 必须等于目录名。
- `description` 必须同时说明 WHAT 和 WHEN。
- 正文必须有一级标题。
- 正文应写给执行 agent，而不是写给最终用户。
- 不要创建 `README.md`、`CHANGELOG.md`、安装说明等与执行无关的辅助文件。

## 触发描述写法

`description` 是最重要的触发信号。写作时偏具体，避免抽象。

必须包含：

- 做什么：能力、任务、产物或领域。
- 何时用：用户措辞、文件类型、系统、工具、错误场景或工作流。
- 关键上下文：平台、语言、框架、组织内术语或接口名称。

较好：

```yaml
description: 为 MODELEX MCP 配置、OpenAI-compatible LLM 配置和配置排查提供工作流。Use when users ask to add MCP servers, configure third-party models, inspect config.json/mcp.json, or diagnose MODELEX configuration issues.
```

较差：

```yaml
description: 配置帮助。
```

## Progressive Disclosure

技能内容按三层组织：

1. Metadata：`name` 和 `description`，始终进入系统上下文。
2. `SKILL.md`：skill 触发后加载，保持短小和流程化。
3. Bundled resources：仅在需要时读取或执行。

资源目录建议：

- `references/`：长文档、schema、协议说明、示例集合。
- `scripts/`：确定性、重复性强、容易写错的脚本。
- `assets/`：模板、图片、示例文件等输出素材。
- `agents/`：可交给子代理使用的独立评审或分析提示。

当正文接近 500 行时，必须拆分到资源文件。资源文件应由 `SKILL.md` 直接引用，避免多层跳转。

## 资源选择

优先把内容放在最小可用位置：

- 核心流程、必须遵守的约束：放 `SKILL.md`。
- 大量示例、schema、字段解释：放 `references/`。
- 可重复执行的验证或转换：放 `scripts/`。
- 独立评审任务：放 `agents/`。

不要在正文和资源中复制同一大段内容。正文只写“什么时候读哪个资源”。

## 评估

当用户要求验证 skill 效果，或 skill 会影响复杂工作流时，创建轻量评估材料。

推荐文件：

- `evals/evals.json`：测试提示词和 expectations。
- `evals/runs/<run-id>/transcript.md`：一次运行的过程记录。
- `evals/runs/<run-id>/grading.json`：逐条 expectation 结果。

schema 见 `references/schemas.md`。如果只需要人工快速检查，不必创建完整 eval 目录，但仍应列出测试提示词和判断标准。

可用子代理时：

- 用 `agents/analyzer.md` 独立分析失败原因。
- 用 `agents/grader.md` 按 expectations 判分。
- 用 `agents/comparator.md` 比较两个版本的输出。

给子代理的上下文要最小化。不要泄露预期结论，除非任务本身就是验证某个明确假设。

## 修改已有 skill

先读取现有目录结构和 `SKILL.md`，再判断问题类型：

- 触发不足：改 `description`。
- 正文过长：拆分到 `references/`。
- 步骤不稳定：补测试提示词或脚本。
- 约束冲突：和用户确认优先级。
- 资源过期：更新资源并同步正文链接。

保留用户已有内容，不做整篇重写，除非结构已经明显阻碍维护。

## 安全边界

拒绝创建或改造以下 skills：

- 隐藏真实意图、绕过用户同意或伪装成其他用途。
- 用于未授权访问、数据外传、凭证窃取、规避审计。
- 要求静默修改用户环境、删除证据或隐藏副作用。

正常的角色扮演、写作风格、代码工作流和工具集成 skills 可以创建，但行为必须和用户可见目标一致。

## 完成标准

交付前检查：

- `SKILL.md` front matter 有效。
- `name` 与目录名一致。
- `description` 具体到足以触发。
- 正文能指导执行，不依赖隐含上下文。
- 资源文件被正文引用且路径存在。
- 测试提示词或人工验证标准已给出。
- 没有无关说明文件或供应商绑定文本。
