"""Test intent parser agent with real DeepSeek LLM."""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from pathlib import Path
import tempfile

def test_intent_parser():
    print("=== Testing Intent Parser Agent ===\n")

    # Setup LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        openai_api_key="sk-c8694451b6c545818a49368ac3f388ea",
        openai_api_base="https://api.deepseek.com",
        temperature=0.7
    )

    # Agent prompt
    agent_prompt = """## 任务
解析用户的 workflow 意图，生成结构化的意图文档。

## 用户输入
"我想要一个代码审查流程，先验证代码质量，如果通过则进行人工审查，最后生成审查报告"

## 输出格式（Markdown）

你需要输出以下格式的 Markdown 文档：

```markdown
# Workflow Intent Analysis

## Workflow Name
[工作流名称，英文下划线]

## Nodes
- **[节点名]**: [功能描述]
  - memory: [ultra_short|short_term|medium_term]
  - tools: [tool1, tool2]

## Flow
[源节点] --> [目标节点] : [条件]
```

## 推断规则
1. 节点识别：从描述中提取动作词
2. 记忆策略：无状态检查→ultra_short，需要对话→short_term，需要历史→medium_term
3. 工具推断：涉及代码→bash_executor，需要搜索→search_long_term

请直接输出 Markdown 文档，不要有其他解释。
"""

    print("Calling LLM...\n")
    response = llm.invoke([SystemMessage(content=agent_prompt)])

    print("=== LLM Output ===")
    print(response.content)
    print("\n=== Validation ===")

    # Check if output contains required sections
    content = response.content
    checks = {
        "Has Workflow Name": "## Workflow Name" in content,
        "Has Nodes section": "## Nodes" in content,
        "Has Flow section": "## Flow" in content,
        "Has memory strategy": "memory:" in content,
        "Has tools": "tools:" in content,
        "Has arrows": "-->" in content
    }

    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"{status} {check}")

    all_passed = all(checks.values())
    print(f"\n{'✓ All checks passed!' if all_passed else '✗ Some checks failed'}")
    return all_passed

if __name__ == "__main__":
    test_intent_parser()
