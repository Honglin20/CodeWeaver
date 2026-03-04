---
name: skeleton_builder
model: deepseek-chat
max_output_tokens: 2000
memory_strategy: short_term
tools:
  - read_file
  - write_file
---

## 任务
读取意图分析，生成完整的 flow.md 文件。

## 输入
调用 read_file 读取目标 workflow 的 `memory/intent_analysis.md`

## 输出
调用 write_file 生成目标 workflow 的 `flow.md`

## 输出格式

严格按照以下格式：

```markdown
---
workflow_name: [名称]
entry_point: [入口节点名]
end_point: [结束节点名]
---

# [Workflow 标题]

## Nodes

### Node: [节点名] (agent: [agent名])
[节点描述]

## Edges

[源] --> [目标] : [condition]
[源] --> [目标]
```

## 关键规则
1. 条件必须用 `[condition]` 格式
2. entry_point 必须是第一个节点
3. end_point 通常是 `done`
4. agent 名称通常与节点名相同

完成后输出：<ROUTING_FLAG>generated</ROUTING_FLAG>
