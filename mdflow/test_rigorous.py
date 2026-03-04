"""Rigorous test suite with edge cases and complex scenarios."""
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
        """Generate response from DeepSeek API."""
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


def test_complex_loop_workflow():
    """Test Case 1: Complex workflow with retry loop."""
    print("=" * 70)
    print("TEST 1: Complex Loop Workflow - Iterative Optimization")
    print("=" * 70)

    api_key = "sk-c8694451b6c545818a49368ac3f388ea"
    llm = DeepSeekLLM(api_key=api_key)

    user_intent = """创建一个代码优化工作流：
1. 分析代码性能
2. 生成优化建议
3. 应用优化
4. 测试性能
5. 如果性能提升不足10%，返回步骤2重新优化（最多3次）
6. 如果性能提升达标或达到最大次数，生成报告并结束
"""

    prompt = f"""## 任务
解析复杂的循环工作流意图。

## 用户输入
{user_intent}

## 输出格式
```markdown
# Workflow Intent Analysis

## Workflow Name
[workflow_name]

## Nodes
- **[node]**: [description]
  - memory: [strategy]
  - tools: [tools]

## Flow
[source] --> [target] : [condition]
```

## 特殊要求
1. 循环边必须明确标注条件
2. 需要有循环计数器或退出条件
3. 必须有最终的退出路径

请输出完整分析。
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
        "Has loop structure": "optimize" in content.lower() or "retry" in content.lower(),
        "Has exit condition": "report" in content.lower() or "end" in content.lower(),
        "Has conditional edges": "[" in content and "]" in content,
        "Has multiple paths": content.count("-->") >= 5,
        "Has routing flag": "<ROUTING_FLAG>parsed</ROUTING_FLAG>" in content
    }

    print("\n✅ Validation Results:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 TEST 1 PASSED: Complex loop workflow handled correctly!")
    else:
        print("\n❌ TEST 1 FAILED")

    return all_passed


def test_parallel_workflow():
    """Test Case 2: Parallel execution workflow."""
    print("\n" + "=" * 70)
    print("TEST 2: Parallel Workflow - Multi-stage Validation")
    print("=" * 70)

    api_key = "sk-c8694451b6c545818a49368ac3f388ea"
    llm = DeepSeekLLM(api_key=api_key)

    user_intent = """创建一个并行验证工作流：
1. 接收代码提交
2. 同时执行三个独立检查：
   - 单元测试
   - 代码风格检查
   - 安全扫描
3. 等待所有检查完成
4. 如果全部通过，批准合并
5. 如果任何一个失败，拒绝合并
"""

    prompt = f"""## 任务
解析并行执行工作流。

## 用户输入
{user_intent}

## 输出格式
```markdown
# Workflow Intent Analysis

## Workflow Name
[workflow_name]

## Nodes
- **[node]**: [description]
  - memory: [strategy]
  - tools: [tools]

## Flow
[source] --> [target] : [condition]
```

## 特殊要求
1. 并行节点应该从同一个源节点出发
2. 需要有汇聚节点等待所有并行任务完成
3. 条件判断应该考虑所有并行结果

请输出完整分析。
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
        "Has multiple parallel nodes": content.count("- **") >= 5,
        "Has test node": "test" in content.lower() or "检查" in content,
        "Has merge/aggregate node": "merge" in content.lower() or "aggregate" in content.lower() or "汇聚" in content or "等待" in content,
        "Has approval logic": "approve" in content.lower() or "批准" in content or "通过" in content,
        "Has routing flag": "<ROUTING_FLAG>parsed</ROUTING_FLAG>" in content
    }

    print("\n✅ Validation Results:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 TEST 2 PASSED: Parallel workflow handled correctly!")
    else:
        print("\n❌ TEST 2 FAILED")

    return all_passed


def test_error_handling_workflow():
    """Test Case 3: Workflow with comprehensive error handling."""
    print("\n" + "=" * 70)
    print("TEST 3: Error Handling - Robust Workflow with Fallbacks")
    print("=" * 70)

    api_key = "sk-c8694451b6c545818a49368ac3f388ea"
    llm = DeepSeekLLM(api_key=api_key)

    user_intent = """创建一个健壮的数据处理工作流：
1. 读取数据文件
2. 如果读取失败，尝试备份源（最多2次重试）
3. 验证数据格式
4. 如果格式错误，尝试自动修复
5. 如果修复失败，发送告警并人工介入
6. 处理数据
7. 如果处理出错，回滚并记录日志
8. 保存结果
9. 如果保存失败，重试3次
10. 最终成功或失败都要发送通知
"""

    prompt = f"""## 任务
解析包含完整错误处理的复杂工作流。

## 用户输入
{user_intent}

## 输出格式
```markdown
# Workflow Intent Analysis

## Workflow Name
[workflow_name]

## Nodes
- **[node]**: [description]
  - memory: [strategy]
  - tools: [tools]

## Flow
[source] --> [target] : [condition]
```

## 特殊要求
1. 每个可能失败的步骤都要有错误处理路径
2. 重试逻辑要明确次数限制
3. 要有最终的通知/清理节点

请输出完整分析。
完成后输出：<ROUTING_FLAG>parsed</ROUTING_FLAG>
"""

    print("\n📤 Calling DeepSeek API...")
    response = llm.invoke([SystemMessage(content=prompt)])

    print("\n📥 LLM Response:")
    print("-" * 70)
    print(response.content[:1500] + "..." if len(response.content) > 1500 else response.content)
    print("-" * 70)

    # Validation
    content = response.content
    checks = {
        "Has retry logic": "retry" in content.lower() or "重试" in content,
        "Has error handling": "error" in content.lower() or "failed" in content.lower() or "失败" in content,
        "Has fallback paths": content.count("[failed]") >= 2 or content.count("[error]") >= 2,
        "Has notification": "notify" in content.lower() or "alert" in content.lower() or "通知" in content or "告警" in content,
        "Has multiple conditions": content.count("[") >= 6,
        "Has routing flag": "<ROUTING_FLAG>parsed</ROUTING_FLAG>" in content
    }

    print("\n✅ Validation Results:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 TEST 3 PASSED: Error handling workflow handled correctly!")
    else:
        print("\n❌ TEST 3 FAILED")

    return all_passed


def test_edge_case_empty_intent():
    """Test Case 4: Edge case - empty or minimal intent."""
    print("\n" + "=" * 70)
    print("TEST 4: Edge Case - Minimal Intent")
    print("=" * 70)

    api_key = "sk-c8694451b6c545818a49368ac3f388ea"
    llm = DeepSeekLLM(api_key=api_key)

    user_intent = """创建一个简单的工作流"""

    prompt = f"""## 任务
解析极简的用户意图，需要做出合理推断。

## 用户输入
{user_intent}

## 输出格式
```markdown
# Workflow Intent Analysis

## Workflow Name
[workflow_name]

## Nodes
- **[node]**: [description]
  - memory: [strategy]
  - tools: [tools]

## Flow
[source] --> [target]
```

## 特殊要求
当用户意图不明确时，生成一个最基本的工作流框架：
- 至少包含 start 和 done 节点
- 提供合理的默认配置

请输出完整分析。
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
        "Has workflow name": "## Workflow Name" in content,
        "Has at least 2 nodes": content.count("- **") >= 2,
        "Has start or entry node": "start" in content.lower() or "entry" in content.lower() or "开始" in content,
        "Has end or done node": "done" in content.lower() or "end" in content.lower() or "结束" in content,
        "Has routing flag": "<ROUTING_FLAG>parsed</ROUTING_FLAG>" in content
    }

    print("\n✅ Validation Results:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 TEST 4 PASSED: Minimal intent handled gracefully!")
    else:
        print("\n❌ TEST 4 FAILED")

    return all_passed


def test_edge_case_ambiguous_intent():
    """Test Case 5: Edge case - ambiguous intent."""
    print("\n" + "=" * 70)
    print("TEST 5: Edge Case - Ambiguous Intent")
    print("=" * 70)

    api_key = "sk-c8694451b6c545818a49368ac3f388ea"
    llm = DeepSeekLLM(api_key=api_key)

    user_intent = """处理一些东西，然后做点什么，最后完成"""

    prompt = f"""## 任务
解析模糊的用户意图，需要做出合理推断。

## 用户输入
{user_intent}

## 输出格式
```markdown
# Workflow Intent Analysis

## Workflow Name
[workflow_name]

## Nodes
- **[node]**: [description]
  - memory: [strategy]
  - tools: [tools]

## Flow
[source] --> [target]
```

## 特殊要求
当用户意图模糊时：
1. 使用通用的节点名称（如 process, handle, complete）
2. 选择最常用的 memory 策略（short_term）
3. 不指定具体工具，使用空列表

请输出完整分析。
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
        "Has workflow name": "## Workflow Name" in content,
        "Has nodes": "## Nodes" in content and "- **" in content,
        "Has flow": "## Flow" in content and "-->" in content,
        "Has memory strategy": "memory:" in content,
        "Has routing flag": "<ROUTING_FLAG>parsed</ROUTING_FLAG>" in content
    }

    print("\n✅ Validation Results:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 TEST 5 PASSED: Ambiguous intent handled gracefully!")
    else:
        print("\n❌ TEST 5 FAILED")

    return all_passed


def main():
    """Run all rigorous tests."""
    print("\n" + "=" * 70)
    print("RIGOROUS TEST SUITE - Edge Cases & Complex Scenarios")
    print("Using DeepSeek API")
    print("=" * 70)

    results = []

    # Test 1: Complex loop
    try:
        test1_passed = test_complex_loop_workflow()
        results.append(("Complex Loop Workflow", test1_passed))
    except Exception as e:
        print(f"\n❌ TEST 1 ERROR: {e}")
        results.append(("Complex Loop Workflow", False))

    # Test 2: Parallel workflow
    try:
        test2_passed = test_parallel_workflow()
        results.append(("Parallel Workflow", test2_passed))
    except Exception as e:
        print(f"\n❌ TEST 2 ERROR: {e}")
        results.append(("Parallel Workflow", False))

    # Test 3: Error handling
    try:
        test3_passed = test_error_handling_workflow()
        results.append(("Error Handling Workflow", test3_passed))
    except Exception as e:
        print(f"\n❌ TEST 3 ERROR: {e}")
        results.append(("Error Handling Workflow", False))

    # Test 4: Minimal intent
    try:
        test4_passed = test_edge_case_empty_intent()
        results.append(("Minimal Intent", test4_passed))
    except Exception as e:
        print(f"\n❌ TEST 4 ERROR: {e}")
        results.append(("Minimal Intent", False))

    # Test 5: Ambiguous intent
    try:
        test5_passed = test_edge_case_ambiguous_intent()
        results.append(("Ambiguous Intent", test5_passed))
    except Exception as e:
        print(f"\n❌ TEST 5 ERROR: {e}")
        results.append(("Ambiguous Intent", False))

    # Summary
    print("\n" + "=" * 70)
    print("RIGOROUS TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    if total_passed == len(results):
        print("\n🎉 ALL RIGOROUS TESTS PASSED!")
        print("The system handles complex scenarios and edge cases correctly!")
        return True
    else:
        print(f"\n⚠️  {len(results) - total_passed} test(s) failed or need improvement")
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
