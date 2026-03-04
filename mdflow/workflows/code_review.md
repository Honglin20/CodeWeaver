---
workflow_name: code_review_workflow
entry_point: review
end_point: done
---

# Code Review Workflow

This workflow reviews code and suggests fixes if needed.

## Nodes

### Node: review (agent: code_reviewer)

Reviews the code file and decides if it needs changes.

### Node: fix (agent: code_fixer)

Suggests improvements for code that needs revision.

### Node: done (agent: code_reviewer)

Final approval step.

## Flow

review --> fix : [needs_revision]
review --> done : [approved]
fix --> done
