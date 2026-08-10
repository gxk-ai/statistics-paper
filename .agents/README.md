# Agent Directory

`.agents/` contains agent-facing capabilities and conventions for this thesis project.

## Active Skill Rule

Only directories matching this pattern are active project Skills:

```text
.agents/skills/<skill-name>/SKILL.md
```

Other folders in the repository may contain imported examples, vendor archives, or historical `SKILL.md` files, but they are not active project Skills unless copied into `.agents/skills/`.

## Responsibilities

- `.agents/skills/` stores what the agent can do.
- `route-map.yml` decides which Skill or workflow is relevant for a task.
- `workflows/` describes how multiple Skills cooperate during a thesis workflow.

Do not store thesis evidence, experiment results, data, or draft chapters here.
