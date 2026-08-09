# Skill Creator Schemas

本文件定义 skill 评估与迭代时可选使用的数据结构。只有在用户要求系统化评估、批量对比或保留评估记录时才需要读取。

## `evals/evals.json`

定义一组测试提示词和可验证期望。

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": "basic-flow",
      "prompt": "把这段工作流整理成一个 skill。",
      "expected_output": "生成完整 SKILL.md，并说明触发场景。",
      "files": [],
      "expectations": [
        "输出包含 YAML front matter",
        "description 同时描述 WHAT 和 WHEN",
        "正文包含可执行步骤"
      ]
    }
  ]
}
```

字段：

- `skill_name`：被评估 skill 的目录名或 front matter `name`。
- `evals[].id`：稳定、可读的用例标识。
- `evals[].prompt`：模拟用户请求。
- `evals[].expected_output`：人工可读成功标准。
- `evals[].files`：可选输入文件列表，路径相对 eval 根目录。
- `evals[].expectations`：逐条可判定的行为期望。

## `evals/runs/<run-id>/grading.json`

记录单次运行的判分结果。

```json
{
  "eval_id": "basic-flow",
  "skill_name": "example-skill",
  "expectations": [
    {
      "text": "输出包含 YAML front matter",
      "passed": true,
      "evidence": "结果开头包含 name 和 description 字段。"
    }
  ],
  "summary": {
    "passed": 1,
    "failed": 0,
    "total": 1,
    "pass_rate": 1.0
  },
  "execution_metrics": {
    "tool_calls": 3,
    "errors_encountered": 0
  },
  "notes": "人工或子代理判分说明。"
}
```

字段：

- `eval_id`：对应 `evals.json` 中的用例标识。
- `skill_name`：被评估 skill。
- `expectations[].text`：原始 expectation。
- `expectations[].passed`：是否满足。
- `expectations[].evidence`：判定依据，引用输出、文件或日志。
- `summary`：聚合结果。
- `execution_metrics`：可选运行指标。
- `notes`：额外观察或限制。

## `evals/runs/<run-id>/comparison.json`

比较两个 skill 版本或两次输出。

```json
{
  "eval_id": "basic-flow",
  "baseline": "v1",
  "candidate": "v2",
  "winner": "candidate",
  "criteria": [
    {
      "name": "triggering",
      "winner": "candidate",
      "reason": "候选版本 description 覆盖了用户实际措辞。"
    }
  ],
  "regressions": []
}
```

字段：

- `baseline`：对照版本。
- `candidate`：候选版本。
- `winner`：`baseline`、`candidate` 或 `tie`。
- `criteria[]`：按维度比较。
- `regressions[]`：候选版本新增问题。

## 评估原则

- 只为复杂或反复迭代的 skill 建立完整 JSON 记录。
- 轻量场景可直接在回复中列出测试提示词和观察结果。
- 判分必须引用证据，不要只写“感觉更好”。
- 如果 expectation 不可判定，先重写 expectation，再继续评估。
