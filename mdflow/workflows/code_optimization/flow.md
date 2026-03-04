---
workflow_name: code_optimization
entry_point: validate
end_point: done
---

# Code Optimization Workflow

## Nodes

### Node: validate (agent: validator)
校验代码质量

### Node: interact (agent: interactor)
与用户交互确认优化方向

### Node: optimize (agent: optimizer)
执行代码优化

### Node: done (agent: validator)
最终验证

## Edges

validate --> interact : [failed]
validate --> done : [passed]
interact --> optimize
optimize --> validate
