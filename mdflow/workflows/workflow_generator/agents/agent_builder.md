---
name: agent_builder
model: deepseek-chat
max_output_tokens: 3000
memory_strategy: medium_term
tools:
  - read_file
  - write_file
---

## 任务
读取 flow.md 和意图分析，为每个节点生成 agent.md 配置。

## 输入
1. 调用 read_file 读取目标 workflow 的 `flow.md`
2. 调用 read_file 读取 `memory/intent_analysis.md`

## 输出
为每个节点调用 write_file 生成 `agents/[节点名].md`

## Agent 配置格式

```markdown
---
name: [agent名称]
model: deepseek-chat
max_output_tokens: 2000
memory_strategy: [ultra_short|short_term|medium_term]
context_file: memory/ultra_short/[agent名]_context.md
tools:
  - [tool1]
  - [tool2]
---

## 任务
[根据节点功能描述任务]

## 输入
[描述输入来源]

## 输出
[描述输出格式和要求]

必须输出：<ROUTING_FLAG>[flag]</ROUTING_FLAG>
```

## Prompt 生成规则
1. 校验节点：输出 passed/failed
2. 交互节点：输出 confirmed/rejected
3. 处理节点：输出 success/error

完成后输出：<ROUTING_FLAG>completed</ROUTING_FLAG>
