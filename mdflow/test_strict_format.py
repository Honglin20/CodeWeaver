"""Improved rigorous test with explicit format requirements."""
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


def test_with_strict_format():
    """Test with extremely strict format requirements."""
    print("=" * 70)
    print("TEST: Strict Format Enforcement")
    print("=" * 70)

    api_key = "sk-c8694451b6c545818a49368ac3f388ea"
    llm = DeepSeekLLM(api_key=api_key)

    user_intent = """创建一个代码审查工作流：
1. 验证代码质量
2. 如果通过则人工审查
3. 如果审查确认则生成报告
4. 如果验证失败则直接结束
"""

    prompt = f"""## 任务
解析用户意图并生成工作流分析。

## 用户输入
{user_intent}

## 输出格式要求

**CRITICAL: 所有条件边必须使用方括号格式，例如 [passed]、[failed]、[confirmed]**

输出格式：
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

## 条件格式规则（必须遵守）

✅ 正确格式：
```
validate --> review : [passed]
validate --> end : [failed]
review --> report : [confirmed]
review --> end : [rejected]
```

❌ 错误格式（禁止使用）：
```
validate --> review : 验证通过  ❌ 不能用中文
validate --> review : passed    ❌ 缺少方括号
validate --> review : 如果通过  ❌ 不能用描述
```

## 标准条件词汇
- 成功/失败: [passed] / [failed]
- 确认/拒绝: [confirmed] / [rejected]
- 成功/错误: [success] / [error]

请严格按照格式输出，所有条件必须用方括号。
完成后输出：<ROUTING_FLAG>parsed</ROUTING_FLAG>
"""

    print("\n📤 Calling DeepSeek API with strict format requirements...")
    response = llm.invoke([SystemMessage(content=prompt)])

    print("\n📥 LLM Response:")
    print("-" * 70)
    print(response.content)
    print("-" * 70)

    # Strict validation
    content = response.content

    # Extract flow section
    flow_section = ""
    if "## Flow" in content:
        flow_start = content.index("## Flow")
        flow_section = content[flow_start:]
        if "<ROUTING_FLAG>" in flow_section:
            flow_end = flow_section.index("<ROUTING_FLAG>")
            flow_section = flow_section[:flow_end]

    # Check for bracket format in conditions
    lines_with_arrows = [line for line in flow_section.split('\n') if '-->' in line]

    bracket_conditions = []
    non_bracket_conditions = []

    for line in lines_with_arrows:
        if ':' in line:  # Has condition
            condition_part = line.split(':')[1].strip()
            if condition_part.startswith('[') and condition_part.endswith(']'):
                bracket_conditions.append(line.strip())
            else:
                non_bracket_conditions.append(line.strip())

    checks = {
        "Has Workflow Name": "## Workflow Name" in content,
        "Has Nodes section": "## Nodes" in content,
        "Has Flow section": "## Flow" in content,
        "Has arrows": "-->" in content,
        "Has routing flag": "<ROUTING_FLAG>parsed</ROUTING_FLAG>" in content,
        "All conditions use brackets": len(non_bracket_conditions) == 0 and len(bracket_conditions) > 0,
        "No Chinese in conditions": not any(ord(c) > 127 for line in lines_with_arrows for c in line.split(':')[-1] if ':' in line)
    }

    print("\n✅ Validation Results:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if non_bracket_conditions:
        print("\n❌ Found conditions without brackets:")
        for line in non_bracket_conditions:
            print(f"  - {line}")

    if bracket_conditions:
        print("\n✅ Correct bracket conditions:")
        for line in bracket_conditions:
            print(f"  - {line}")

    if all_passed:
        print("\n🎉 TEST PASSED: All conditions use correct bracket format!")
    else:
        print("\n❌ TEST FAILED: Some conditions don't use bracket format")

    return all_passed


def main():
    """Run strict format test."""
    print("\n" + "=" * 70)
    print("STRICT FORMAT VALIDATION TEST")
    print("Testing if LLM follows bracket format requirements")
    print("=" * 70)

    try:
        success = test_with_strict_format()

        if success:
            print("\n🎉 SUCCESS: LLM correctly uses bracket format!")
            print("Ready to proceed with full workflow generation.")
        else:
            print("\n⚠️  NEEDS IMPROVEMENT: LLM not following bracket format")
            print("Recommendation: Further optimize agent prompts or add post-processing")

        return success
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
