# 系统整体架构设计

## 概述

MDFlow 采用四层记忆架构，支持多智能体协作。

## 核心组件

- Parser: 解析 Markdown 配置
- MemoryManager: 管理四层记忆
- Compiler: 编译为 LangGraph
- Executor: 执行工作流
