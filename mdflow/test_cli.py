"""Test CLI with real LLM end-to-end."""
import sys
import subprocess
from pathlib import Path
import shutil


def run_command(cmd):
    """Run shell command and return output."""
    print(f"\n💻 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"⚠️  stderr: {result.stderr}")
    return result.returncode, result.stdout, result.stderr


def test_cli_validate():
    """Test CLI validate command."""
    print("=" * 70)
    print("TEST 1: CLI Validate Command")
    print("=" * 70)

    returncode, stdout, stderr = run_command("python3 cli.py validate workflows/workflow_generator/")

    checks = {
        "Command executed successfully": returncode == 0,
        "Output contains validation message": "Validating workflow" in stdout,
        "Validation passed": "passed" in stdout.lower() or "✓" in stdout
    }

    print("\n✅ Validation:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    return all_passed


def test_cli_normalize():
    """Test CLI normalize command."""
    print("\n" + "=" * 70)
    print("TEST 2: CLI Normalize Command")
    print("=" * 70)

    # Create test input with format issues
    test_input = """# Workflow Intent Analysis

## Workflow Name
test_workflow

## Nodes
- **validate**: Validate code
  - memory: short_term
  - tools: [linter]

## Flow
validate --> done : 验证通过

<ROUTING_FLAG>parsed</ROUTING_FLAG>
"""

    test_file = Path("/tmp/test_cli_input.md")
    test_file.write_text(test_input, encoding='utf-8')

    returncode, stdout, stderr = run_command(f"python3 cli.py normalize {test_file}")

    checks = {
        "Command executed successfully": returncode == 0,
        "Output contains normalized content": "Normalized Output" in stdout,
        "Chinese condition was fixed": "[passed]" in stdout,
        "Changes were reported": "Changes made" in stdout
    }

    print("\n✅ Validation:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    # Cleanup
    test_file.unlink()

    return all_passed


def test_cli_help():
    """Test CLI help command."""
    print("\n" + "=" * 70)
    print("TEST 3: CLI Help Command")
    print("=" * 70)

    returncode, stdout, stderr = run_command("python3 cli.py --help")

    checks = {
        "Command executed successfully": returncode == 0,
        "Shows usage": "usage:" in stdout.lower(),
        "Shows commands": "generate" in stdout and "validate" in stdout,
        "Shows examples": "Examples:" in stdout
    }

    print("\n✅ Validation:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    return all_passed


def test_cli_version():
    """Test CLI version command."""
    print("\n" + "=" * 70)
    print("TEST 4: CLI Version Command")
    print("=" * 70)

    returncode, stdout, stderr = run_command("python3 cli.py --version")

    checks = {
        "Command executed successfully": returncode == 0,
        "Shows version": "0.1.0" in stdout or "0.1.0" in stderr
    }

    print("\n✅ Validation:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False

    return all_passed


def main():
    """Run all CLI tests."""
    print("\n" + "=" * 70)
    print("CLI END-TO-END TEST SUITE")
    print("Testing all CLI commands")
    print("=" * 70)

    results = []

    # Test 1: Validate
    try:
        result = test_cli_validate()
        results.append(("CLI Validate", result))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        results.append(("CLI Validate", False))

    # Test 2: Normalize
    try:
        result = test_cli_normalize()
        results.append(("CLI Normalize", result))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        results.append(("CLI Normalize", False))

    # Test 3: Help
    try:
        result = test_cli_help()
        results.append(("CLI Help", result))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        results.append(("CLI Help", False))

    # Test 4: Version
    try:
        result = test_cli_version()
        results.append(("CLI Version", result))
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        results.append(("CLI Version", False))

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
        print("\n🎉 ALL CLI TESTS PASSED!")
        print("CLI tool is fully functional!")
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
