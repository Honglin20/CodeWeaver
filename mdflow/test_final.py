"""Final comprehensive test with improved prompts."""
import os
import sys
from pathlib import Path

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
        api_messages = []
        for msg in messages:
            if hasattr(msg, 'content'):
                role = "system" if isinstance(msg, SystemMessage) else "user"
                api_messages.append({"role": role, "content": msg.content})

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
        return self


def create_improved_prompt(user_intent, scenario_name):
    """Create improved prompt with explicit format examples."""
    return f"""## 任务
解析用户的工作流意图，生成结构化分析。

## 用户输入
{user_intent}

## 输出格式

```markdown
# Workflow Intent Analysis

## Workflow Name
[workflow_name]

## Nodes
- **[node_name]**: [description]
  - memory: [ultra_short|short_term|medium_term]
  - tools: [tool1, tool2]

## Flow
[source] --> [target] : [condition]
[source] --> [target]
```

## 条件格式规则（CRITICAL）

**所有条件必须使用方括号格式**

✅ 正确示例：
```
validate --> process : [passed]
validate --> end : [failed]
review --> approve : [confirmed]
test --> retry : [retry]
test --> done : [complete]
```

❌ 错误示例（禁止）：
```
validate --> process : 验证通过    ❌ 不能用中文
validate --> process : passed      ❌ 缺少方括号
test --> retry : 性能<10%          ❌ 不能用表达式
test --> next : always             ❌ 不能用 always
```

## 标准条件词汇
- [passed] / [failed]
- [confirmed] / [rejected]
- [success] / [error]
- [retry] / [complete]
- [timeout]

请严格按照格式输出。
完成后输出：<ROUTING_FLAG>parsed</ROUTING_FLAG>
"""


def test_scenario(api_key, scenario_name, user_intent, validation_checks):
    """Test a specific scenario."""
    print("=" * 70)
    print(f"TEST: {scenario_name}")
    print("=" * 70)

    llm = DeepSeekLLM(api_key=api_key)
    prompt = create_improved_prompt(user_intent, scenario_name)

    print("\n📤 Calling DeepSeek API...")
    response = llm.invoke([SystemMessage(content=prompt)])

    print("\n📥 LLM Response:")
    print("-" * 70)
    print(response.content[:800] + "..." if len(response.content) > 800 else response.content)
    print("-" * 70)

    # Validate
    content = response.content

    # Check bracket format
    flow_section = ""
    if "## Flow" in content:
        flow_start = content.index("## Flow")
        flow_section = content[flow_start:]
        if "<ROUTING_FLAG>" in flow_section:
            flow_end = flow_section.index("<ROUTING_FLAG>")
            flow_section = flow_section[:flow_end]

    lines_with_arrows = [line for line in flow_section.split('\n') if '-->' in line]
    bracket_conditions = []
    non_bracket_conditions = []

    for line in lines_with_arrows:
        if ':' in line:
            condition_part = line.split(':')[1].strip()
            if condition_part.startswith('[') and condition_part.endswith(']'):
                bracket_conditions.append(line.strip())
            else:
                non_bracket_conditions.append(line.strip())

    # Run validation checks
    checks = validation_checks(content, bracket_conditions, non_bracket_conditions)

    print("\n✅ Validation Results:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if non_bracket_conditions:
        print(f"\n⚠️  Found {len(non_bracket_conditions)} conditions without brackets:")
        for line in non_bracket_conditions[:3]:
            print(f"  - {line}")

    if all_passed:
        print(f"\n🎉 {scenario_name} PASSED!")
    else:
        print(f"\n❌ {scenario_name} FAILED")

    return all_passed


def main():
    """Run all final tests."""
    print("\n" + "=" * 70)
    print("FINAL COMPREHENSIVE TEST SUITE")
    print("With Improved Prompts")
    print("=" * 70)

    api_key = "sk-c8694451b6c545818a49368ac3f388ea"
    results = []

    # Test 1: Simple workflow
    def validate_simple(content, bracket_conds, non_bracket_conds):
        return {
            "Has workflow name": "## Workflow Name" in content,
            "Has nodes": "## Nodes" in content,
            "Has flow": "## Flow" in content,
            "All conditions use brackets": len(non_bracket_conds) == 0,
            "Has routing flag": "<ROUTING_FLAG>parsed</ROUTING_FLAG>" in content
        }

    try:
        result = test_scenario(
            api_key,
            "Simple Code Review Workflow",
            """创建代码审查工作流：
1. 验证代码质量
2. 如果通过则人工审查
3. 如果确认则生成报告
4. 如果失败则结束""",
            validate_simple
        )
        results.append(("Simple Workflow", result))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        results.append(("Simple Workflow", False))

    # Test 2: Loop workflow
    def validate_loop(content, bracket_conds, non_bracket_conds):
        return {
            "Has workflow name": "## Workflow Name" in content,
            "Has loop structure": "optimize" in content.lower() or "retry" in content.lower(),
            "All conditions use brackets": len(non_bracket_conds) == 0,
            "Has exit condition": "done" in content.lower() or "complete" in content.lower(),
            "Has routing flag": "<ROUTING_FLAG>parsed</ROUTING_FLAG>" in content
        }

    try:
        result = test_scenario(
            api_key,
            "Loop Workflow with Retry",
            """创建优化循环工作流：
1. 分析性能
2. 生成优化建议
3. 应用优化
4. 测试性能
5. 如果提升不足则重试（最多3次）
6. 如果达标则生成报告""",
            validate_loop
        )
        results.append(("Loop Workflow", result))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        results.append(("Loop Workflow", False))

    # Test 3: Parallel workflow
    def validate_parallel(content, bracket_conds, non_bracket_conds):
        return {
            "Has workflow name": "## Workflow Name" in content,
            "Has multiple nodes": content.count("- **") >= 5,
            "All conditions use brackets": len(non_bracket_conds) == 0,
            "Has merge logic": "merge" in content.lower() or "aggregate" in content.lower() or "汇聚" in content,
            "Has routing flag": "<ROUTING_FLAG>parsed</ROUTING_FLAG>" in content
        }

    try:
        result = test_scenario(
            api_key,
            "Parallel Validation Workflow",
            """创建并行验证工作流：
1. 接收代码
2. 同时执行：单元测试、代码检查、安全扫描
3. 汇聚结果
4. 如果全部通过则批准
5. 如果任何失败则拒绝""",
            validate_parallel
        )
        results.append(("Parallel Workflow", result))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        results.append(("Parallel Workflow", False))

    # Summary
    print("\n" + "=" * 70)
    print("FINAL TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    if total_passed == len(results):
        print("\n🎉 ALL TESTS PASSED!")
        print("Workflow generation system is working correctly!")
        return True
    else:
        print(f"\n⚠️  {len(results) - total_passed} test(s) failed")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
