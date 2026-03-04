# Structured Memory Update

## 新增功能

### 四层记忆架构

1. **超短期记忆**：无状态 context，从 agent.md 配置
2. **短期记忆**：滑动窗口，按 session 隔离
3. **中期记忆**：任务日志，JSONL + MD 双写
4. **长期记忆**：知识库，支持搜索

### 核心改进

- ✅ 文件锁机制（fcntl）
- ✅ 按 session 隔离（无并发冲突）
- ✅ JSON 容错（自动备份）
- ✅ 正则安全解析
- ✅ 5 个测试全部通过

### 示例工作流

`workflows/code_optimization/` 包含完整示例：
- flow.md: 工作流定义
- agents/: 三个 agent 配置
- memory/: 四层记忆结构
- tools/: 工具定义
- config.yaml: 配置参数

## 测试结果

```
5 passed in 0.08s
```

## 下一步

集成到 Compiler，实现完整的执行引擎。
