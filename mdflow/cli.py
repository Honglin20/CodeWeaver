"""MDFlow CLI - Command-line interface for workflow generation and execution."""
import sys
import argparse
from pathlib import Path
from typing import Optional

from core.post_processor import normalize_workflow_output
from core.validation import validate_workflow, print_validation_results


def cmd_generate(args):
    """Generate workflow from natural language description."""
    print(f"🚀 Generating workflow from: {args.description}")
    print(f"📁 Output directory: {args.output}")

    # TODO: Implement workflow generation
    print("\n⚠️  Workflow generation not yet implemented")
    print("This will call the workflow_generator meta-workflow")

    return 0


def cmd_validate(args):
    """Validate workflow configuration."""
    print(f"🔍 Validating workflow: {args.workflow_dir}")

    try:
        errors = validate_workflow(args.workflow_dir)
        success = print_validation_results(errors)

        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Validation error: {e}")
        return 1


def cmd_run(args):
    """Execute workflow."""
    print(f"▶️  Running workflow: {args.workflow_dir}")
    print(f"📝 Session ID: {args.session}")

    # TODO: Implement workflow execution
    print("\n⚠️  Workflow execution not yet implemented")
    print("This will compile and execute the workflow")

    return 0


def cmd_normalize(args):
    """Normalize LLM output format."""
    print(f"🔧 Normalizing file: {args.input}")

    try:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"❌ File not found: {args.input}")
            return 1

        content = input_path.read_text(encoding='utf-8')
        result = normalize_workflow_output(content)

        if args.output:
            output_path = Path(args.output)
            output_path.write_text(result.content, encoding='utf-8')
            print(f"✅ Normalized output written to: {args.output}")
        else:
            print("\n📤 Normalized Output:")
            print("-" * 70)
            print(result.content)
            print("-" * 70)

        if result.changes_made:
            print(f"\n🔧 Changes made: {len(result.changes_made)}")
            for change in result.changes_made:
                print(f"  - {change}")

        if result.warnings:
            print(f"\n⚠️  Warnings: {len(result.warnings)}")
            for warning in result.warnings:
                print(f"  - {warning}")

        return 0
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='mdflow',
        description='MDFlow - Configuration-driven multi-agent workflow system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate workflow from description
  mdflow generate "Create code review workflow" -o output/

  # Validate workflow
  mdflow validate workflows/my_workflow/

  # Run workflow
  mdflow run workflows/my_workflow/ --session test_001

  # Normalize LLM output
  mdflow normalize input.md -o output.md
        """
    )

    parser.add_argument('--version', action='version', version='mdflow 0.1.0')

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate workflow from description')
    generate_parser.add_argument('description', help='Natural language workflow description')
    generate_parser.add_argument('-o', '--output', required=True, help='Output directory')
    generate_parser.add_argument('--model', default='deepseek-chat', help='LLM model to use')
    generate_parser.set_defaults(func=cmd_generate)

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate workflow configuration')
    validate_parser.add_argument('workflow_dir', help='Workflow directory to validate')
    validate_parser.set_defaults(func=cmd_validate)

    # Run command
    run_parser = subparsers.add_parser('run', help='Execute workflow')
    run_parser.add_argument('workflow_dir', help='Workflow directory to run')
    run_parser.add_argument('--session', default='default', help='Session ID')
    run_parser.add_argument('--model', default='deepseek-chat', help='LLM model to use')
    run_parser.set_defaults(func=cmd_run)

    # Normalize command
    normalize_parser = subparsers.add_parser('normalize', help='Normalize LLM output format')
    normalize_parser.add_argument('input', help='Input file to normalize')
    normalize_parser.add_argument('-o', '--output', help='Output file (default: stdout)')
    normalize_parser.set_defaults(func=cmd_normalize)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
