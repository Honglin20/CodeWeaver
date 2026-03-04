"""Test workflow generation with real DeepSeek LLM."""
import os
import sys
from pathlib import Path
import shutil
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from langchain_core.messages import SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.messages import AIMessage
import httpx


class DeepSeekLLM(BaseChatModel):
    """Simple DeepSeek LLM wrapper."""

    api_key: str
    api_base: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.7

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """Generate response from DeepSeek API."""
        # Convert messages to API format
        api_messages = []
        for msg in messages:
            if hasattr(msg, 'content'):
                role = "system" if isinstance(msg, SystemMessage) else "user"
                api_messages.append({"role": role, "content": msg.content})

        # Call API
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": api_messages,
            "temperature": self.temperature
        }

        response = httpx.post(
            f"{self.api_base}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60.0
        )

        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")

        result = response.json()
        content = result['choices'][0]['message']['content']

        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    def _llm_type(self):
        return "deepseek"

    def bind_tools(self, tools):
        """Mock tool binding."""
        return self


def test_intent_parser():
    """Test Case 1: Intent Parser Agent."""
    print("=" * 70)
    print("TEST 1: Intent Parser - Parse User Intent")
    print("=" * 70)

    # Setup LLM
    api_key = "sk-c8694451b6c545818a49368ac3f388ea"
    llm = DeepSeekLLM(api_key=api_key)

    # Test prompt
    user_intent = """我想要一个代码审查流程：
1. 先验证代码质量（运行测试）
2. 如果通过则进行人工审查
3. 审查通过后生成报告
4. 如果验证失败则直接结束
"""

    prompt = f"""## 任务
解析用户的 workflow 意图，生成结构化分析文档。

## 用户输入
{user_intent}

## 输出格式

必须严格按照以下 Markdown 格式：

```markdown
# Workflow Intent Analysis

## Workflow Name
[英文名称，使用下划线分隔，例如：code_review]

## Nodes
- **[节点名]**: [功能描述]
  - memory: [ultra_short|short_term|medium_term]
  - tools: [tool1, tool2]

## Flow
[源节点] --> [目标节点] : [condition]
[源节点] --> [目标节点]
```

## 关键规则
1. **条件格式**：必须用方括号，例如 `[passed]` `[failed]` `[confirmed]`
2. **节点名**：英文下划线格式
3. **Memory 推断**：
   - 无状态检查（如校验）→ ultra_short
   - 需要对话上下文 → short_term
   - 需要任务历史 → medium_term
4. **工具推断**：
   - 执行命令 → mock_test_runner
   - 读写文件 → read_file, write_file

请直接输出 Markdown 文档，不要有其他解释。
完成后输出：<ROUTING_FLAG>parsed</ROUTING_FLAG>
"""

    print("\n📤 Calling DeepSeek API...")
    response = llm.invoke([SystemMessage(content=prompt)])

    print("\n📥 LLM Response:")
    print("-" * 70)
    print(response.content)
    print("-" * 70)

    # Validation
    content = response.content
    checks = {
        "Has Workflow Name section": "## Workflow Name" in content,
        "Has Nodes section": "## Nodes" in content,
        "Has Flow section": "## Flow" in content,
        "Has memory strategy": "memory:" in content,
        "Has tools": "tools:" in content,
        "Has arrows": "-->" in content,
        "Has routing flag": "<ROUTING_FLAG>parsed</ROUTING_FLAG>" in content,
        "Uses brackets for conditions": "[" in content and "]" in content
    }

    print("\n✅ Validation Results:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 TEST 1 PASSED: Intent parser works correctly!")
    else:
        print("\n❌ TEST 1 FAILED: Some checks did not pass")

    return all_passed, response.content


def test_skeleton_builder(intent_analysis):
    """Test Case 2: Skeleton Builder Agent."""
    print("\n" + "=" * 70)
    print("TEST 2: Skeleton Builder - Generate flow.md")
    print("=" * 70)

    # Setup LLM
    api_key = "sk-c8694451b6c545818a49368ac3f388ea"
    llm = DeepSeekLLM(api_key=api_key)

    prompt = f"""## 任务
读取意图分析，生成完整的 flow.md 文件。

## 输入
以下是意图分析内容：

{intent_analysis}
式

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

请直接输出完整的 flow.md 内容，包括 YAML frontmatter。
完成后输出：<ROUTING_FLAG>generated</ROUTING_FLAG>
"""

    print("\n📤 Calling DeepSeek API...")
    response = llm.invoke([SystemMessage(content=prompt)])

    print("\n📥 LLM Response:")
    print("-" * 70)
    print(response.content)
    print("-" * 70)

    # Validation
    content = response.content
    checks = {
        "Has YAML frontmatter": "---" in content and "workflow_name:" in content,
        "Has entry_point": "entry_point:" in content,
        "Has end_point": "end_point:" in content,
        "Has Nodes section": "## Nodes" in content,
        "Has Edges section": "## Edges" in content,
        "Has node definitions": "### Node:" in content,
        "Has agent references": "(agent:" in content,
        "Has routing flag": "<ROUTING_FLAG>generated</ROUTING_FLAG>" in content
    }

    print("\n✅ Validation Results:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 TEST 2 PASSED: Skeleton builder works correctly!")
    else:
        print("\n❌ TEST 2 FAILED: Some checks did not pass")

    return all_passed, response.content


def test_agent_builder(flow_md, intent_analysis):
    """Test Case 3: Agent Builder - Generate agent.md files."""
    print("\n" + "=" * 70)
    print("TEST 3: Agent Builder - Generate agent.md files")
    print("=" * 70)

    # Setup LLM
    api_key = "sk-c8694451b6c545818a49368ac3f388ea"
    llm = DeepSeekLLM(api_key=api_key)

    prompt = f"""## 任务
读取 flow.md 和意图分析，为每个节点生成 agent.md 配置。

## 输入

### flow.md:
{flow_md}

### intent_analysis.md:
{intent_analysis}

## 输出

为每个节点生成 agent.md 配置，格式如下：

```markdown
---
name: [agent名称]
model: deepseek-chat
max_output_tokens: 2000
memory_strategy: [ultra_short|short_term|medium_term]
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

请为每个节点生成一个 agent 配置，用 "---AGENT: [节点名]---" 分隔。
完成后输出：<ROUTING_FLAG>completed</ROUTING_FLAG>
"""

    print("\n📤 Calling DeepSeek API...")
    response = llm.invoke([SystemMessage(content=prompt)])

    print("\n📥 LLM Response:")
    print("-" * 70)
    print(response.content[:1000] + "..." if len(response.content) > 1000 else response.content)
    print("-" * 70)

    # Validation
    content = response.content
    checks = {
        "Has agent separators": "---AGENT:" in content or "name:" in content,
        "Has YAML frontmatter": "---" in content and "name:" in content,
        "Has model field": "model:" in content,
        "Has memory_strategy": "memory_strategy:" in content,
        "Has tools field": "tools:" in content,
        "Has task section": "## 任务" in content or "## Task" in content,
        "Has routing flag": "<ROUTING_FLAG>" in content
    }

    print("\n✅ Validation Results:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 TEST 3 PASSED: Agent builder works correctly!")
    else:
        print("\n❌ TEST 3 FAILED: Some checks did not pass")

    return all_passed, response.content


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("REAL LLM WORKFLOW GENERATION TEST SUITE")
    print("Using DeepSeek API")
    print("=" * 70)

    results = []

    # Test 1: Intent Parser
    test1_passed, intent_analysis = test_intent_parser()
    results.append(("Intent Parser", test1_passed))

    if not test1_passed:
        print("\n⚠️  Stopping tests - Intent parser failed")
        return False

    # Test 2: Skeleton Builder
    test2_passed, flow_md = test_skeleton_builder(intent_analysis)
    results.append(("Skeleton Builder", test2_passed))

    if not test2_passed:
        print("\n⚠️  Stopping tests - Skeleton builder failed")
        return False

    # Test 3: Agent Builder
    test3_passed, agents = test_agent_builder(flow_md, intent_analysis)
    results.append(("Agent Builder", test3_passed))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    if total_passed == len(results):
        print("\n🎉 ALL TESTS PASSED! Workflow generation works correctly with real LLM!")
        return True
    else:
        print(f"\n❌ {len(results) - total_passed} test(s) failed")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
