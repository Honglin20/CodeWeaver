"""Test post-processor with real LLM output."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.post_processor import normalize_workflow_output


def test_normalize_chinese_conditions():
    """Test normalizing Chinese conditions to bracket format."""
    print("=" * 70)
    print("TEST 1: Normalize Chinese Conditions")
    print("=" * 70)

    # Simulated LLM output with Chinese conditions
    raw_output = """# Workflow Intent Analysis

## Workflow Name
code_review

## Nodes
- **validate**: Validate code
  - memory: short_term
  - tools: [linter]
- **review**: Manual review
  - memory: medium_term
  - tools: [review_tool]
- **done**: End
  - memory: ultra_short
  - tools: []

## Flow
validate --> review : 验证通过
validate --> done : 验证失败
review --> done : 审查确认

<ROUTING_FLAG>parsed</ROUTING_FLAG>
"""

    print("\n📥 Raw LLM Output:")
    print("-" * 70)
    print(raw_output)
    print("-" * 70)

    # Normalize
    result = normalize_workflow_output(raw_output)

    print("\n📤 Normalized Output:")
    print("-" * 70)
    print(result.content)
    print("-" * 70)

    print("\n🔧 Changes Made:")
    for change in result.changes_made:
        print(f"  - {change}")

    if result.warnings:
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    # Validate
    checks = {
        "Contains [passed]": "[passed]" in result.content,
        "Contains [failed]": "[failed]" in result.content,
        "Contains [confirmed]": "[confirmed]" in result.content,
        "No Chinese in conditions": not any(
            ord(c) > 127 for line in result.content.split('\n')
            if '-->' in line and ':' in line
            for c in line.split(':')[-1]
        ),
        "Changes were made": len(result.changes_made) > 0
    }

    print("\n✅ Validation:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 TEST 1 PASSED!")
    else:
        print("\n❌ TEST 1 FAILED")

    return all_passed


def test_normalize_expression_conditions():
    """Test normalizing expression-based conditions."""
    print("\n" + "=" * 70)
    print("TEST 2: Normalize Expression Conditions")
    print("=" * 70)

    raw_output = """# Workflow Intent Analysis

## Workflow Name
optimization_loop

## Nodes
- **test**: Test performance
  - memory: short_term
  - tools: [benchmark]
- **optimize**: Apply optimization
  - memory: short_term
  - tools: [optimizer]
- **done**: Complete
  - memory: ultra_short
  - tools: []

## Flow
test --> optimize : 性能提升<10%
test --> done : 性能提升>=10%
optimize --> test : 继续优化

<ROUTING_FLAG>parsed</ROUTING_FLAG>
"""

    print("\n📥 Raw LLM Output:")
    print("-" * 70)
    print(raw_output)
    print("-" * 70)

    result = normalize_workflow_output(raw_output)

    print("\n📤 Ntput:")
    print("-" * 70)
    print(result.content)
    print("-" * 70)

    print("\n🔧 Changes Made:")
    for change in result.changes_made:
        print(f"  - {change}")

    # Validate
    checks = {
        "Contains [retry]": "[retry]" in result.content,
        "Contains [complete]": "[complete]" in result.content,
        "No expressions in conditions": not any(
            '<' in line or '>' in line or '%' in line
            for line in result.content.split('\n')
            if '-->' in line and ':' in line
        ),
        "Changes were made": len(result.changes_made) > 0
    }

    print("\n✅ Validation:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 TEST 2 PASSED!")
    else:
        print("\n❌ TEST 2 FAILED")

    return all_passed


def test_normalize_missing_brackets():
    """Test normalizing conditions without brackets."""
    print("\n" + "=" * 70)
    print("TEST 3: Normalize Missing Brackets")
    print("=" * 70)

    raw_output = """# Workflow Intent Analysis

## Workflow Name
simple_flow

## Nodes
- **start**: Start
  - memory: ultra_short
  - tools: []
- **process**: Process
  - memory: short_term
  - tools: [processor]
- **done**: Done
  - memory: ultra_short
  - tools: []

## Flow
start --> process : success
process --> done : completed

<ROUTING_FLAG>parsed</ROUTING_FLAG>
"""

    print("\n📥 Raw LLM Output:")
    print("-" * 70)
    print(raw_output)
    print("-" * 70)

    result = normalize_workflow_output(raw_output)

    print("\n📤 Normalized Output:")
    print("-" * 70)
    print(result.content)
    print("-" * 70)

    print("\n🔧 Changes Made:")
    for change in result.changes_made:
        print(f"  - {change}")

    # Validate
    checks = {
        "Contains [success]": "[success]" in result.content or "[passed]" in result.content,
        "Contains [complete]": "[complete]" in result.content,
        "All conditions have brackets": all(
            '[' in line.split(':')[-1] and ']' in line.split(':')[-1]
            for line in result.content.split('\n')
            if '-->' in line and ':' in line
        ),
        "Changes were made": len(result.changes_made) > 0
    }

    print("\n✅ Validation:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 TEST 3 PASSED!")
    else:
        print("\n❌ TEST 3 FAILED")

    return all_passed


def main():
    """Run all post-processor tests."""
    print("\n" + "=" * 70)
    print("POST-PROCESSOR TEST SUITE")
    print("Testing automatic format normalization")
    print("=" * 70)

    results = []

    # Test 1: Chinese conditions
    try:
        result = test_normalize_chinese_conditions()
        results.append(("Chinese Conditions", result))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Chinese Conditions", False))

    # Test 2: Expression conditions
    try:
        result = test_normalize_expression_conditions()
        results.append(("Expression Conditions", result))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Expression Conditions", False))

    # Test 3: Missing brackets
    try:
        result = test_normalize_missing_brackets()
        results.append(("Missing Brackets", result))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Missing Brackets", False))

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
        print("\n🎉 ALL TESTS PASSED!")
        print("Post-processor successfully normalizes all format issues!")
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
