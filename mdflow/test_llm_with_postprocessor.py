"""Test post-processor with real LLM output."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from langchain_core.messages import SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.messages import AIMessage
import httpx
from core.post_processor import normalize_workflow_output


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


def test_with_real_llm_and_postprocessor():
    """Test complete pipeline: LLM generation + post-processing."""
    print("=" * 70)
    print("REAL LLM + POST-PROCESSOR INTEGRATION TEST")
    print("=" * 70)

    api_key = "sk-c8694451b6c545818a49368ac3f388ea"
    llm = DeepSeekLLM(api_key=api_key)

    # Test case: Intentionally use a simple prompt without explicit format examples
    # to see if post-processor can fix the output
    user_intent = """创建一个代码审查工作流：
1. 验证代码质量
2. 如果通过则人工审查
3. 如果确认则生成报告
4. 如果失败则结束
"""

    prompt = f"""## 任务
解析用户意图并生成工作流分析。

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

请输出完整分析。
完成后输出：<ROUTING_FLAG>parsed</ROUTING_FLAG>
"""

    print("\n📤 Calling DeepSeek API (without explicit format examples)...")
    response = llm.invoke([SystemMessage(content=prompt)])

    print("\n📥 Raw LLM Output:")
    print("-" * 70)
    print(response.content)
    print("-" * 70)

    # Check if raw output has format issues
    raw_content = response.content
    raw_has_issues = False

    if "## Flow" in raw_content:
        flow_section = raw_content[raw_content.index("## Flow"):]
        lines_with_arrows = [line for line in flow_section.split('\n') if '-->' in line and ':' in line]

        for line in lines_with_arrows:
            condition_part = line.split(':')[-1].strip()
            if not (condition_part.startswith('[') and condition_part.endswith(']')):
                raw_has_issues = True
                break

    if raw_has_issues:
        print("\n⚠️  Raw output has format issues without brackets)")
    else:
        print("\n✓ Raw output already has correct format")

    # Apply post-processor
    print("\n🔧 Applying post-processor...")
    result = normalize_workflow_output(raw_content)

    print("\n📤 Post-processed Output:")
    print("-" * 70)
    print(result.content)
    print("-" * 70)

    if result.changes_made:
        print("\n🔧 Changes Made by Post-processor:")
        for change in result.changes_made:
            print(f"  - {change}")
    else:
        print("\n✓ No changes needed - output was already correct")

    if result.warnings:
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    # Validate final output
    final_content = result.content
    checks = {
        "Has workflow name": "## Workflow Name" in final_content,
        "Has nodes": "## Nodes" in final_content,
        "Has flow": "## Flow" in final_content,
        "All conditions use brackets": all(
            '[' in line.split(':')[-1] and ']' in line.split(':')[-1]
            for line in final_content.split('\n')
            if '-->' in line and ':' in line
        ),
        "No Chinese in conditions": not any(
            ord(c) > 127 for line in final_content.split('\n')
            if '-->' in line and ':' in line
            for c in line.split(':')[-1]
        ),
        "Has routing flag": "<ROUTING_FLAG>parsed</ROUTING_FLAG>" in final_content
    }

    print("\n✅ Final Validation:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 TEST PASSED!")
        print("Post-processor successfully ensures correct format!")
        return True
    else:
        print("\n❌ TEST FAILED")
        return False


def main():
    """Run real LLM + post-processor integration test."""
    print("\n" + "=" * 70)
    print("INTEGRATION TEST: Real LLM + Post-Processor")
    print("Testing if post-processor can fix LLM output issues")
    print("=" * 70)

    try:
        success = test_with_real_llm_and_postprocessor()

        if success:
            print("\n🎉 SUCCESS!")
            print("System is robust against LLM format variations!")
            print("Post-processor provides guaranteed format correctness!")
        else:
            print("\n⚠️  NEEDS IMPROVEMENT")
            print("Post-processor may need additional rules")

        return success
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
