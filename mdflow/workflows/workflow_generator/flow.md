---
workflow_name: workflow_generator
entry_point: parse_intent
end_point: done
---

# Workflow Generator

## Nodes

### Node: parse_intent (agent: intent_parser)
解析用户意图，提取节点和流程信息

### Node: generate_skeleton (agent: skeleton_builder)
生成 flow.md 骨架

### Node: generate_agents (agent: agent_builder)
生成 agent 配置文件

### Node: done (agent: agent_builder)
完成

## Edges

parse_intent --> generate_skeleton
generate_skeleton --> generate_agents
generate_agents --> done
