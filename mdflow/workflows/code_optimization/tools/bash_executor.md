---
tool_name: bash_executor
type: command_executor
timeout: 30
---

## Tool Description

执行 bash 命令的工具

## Command Templates

### run_tests
```bash
pytest {test_path} -v --tb=short
```

### check_syntax
```bash
python -m py_compile {file_path}
```

## Usage

Agent 调用时使用：
- tool: bash_executor
- template: run_tests
- args: {test_path: "tests/"}
