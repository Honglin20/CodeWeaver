# Workflow Generation Design

## Date
2026-03-04

## Overview
Enable LLM-based workflow generation where users provide natural language intent and the system automatically generates workflow and agent configurations.

## Architecture

### Core Principle
The generator itself is a workflow (`workflow_generator`), not standalone classes. This follows the existing atomic capability pattern.

### Meta-Workflow Structure

```
workflows/workflow_generator/
├── flow.md                    # Generator workflow definition
├── agents/
│   ├── intent_parser.md       # Parse user intent
│   ├── skeleton_builder.md    # Generate flow.md
│   └── agent_builder.md       # Generate agent.md files
└── memory/
    └── ultra_short/
        └── parser_context.md
```

### Flow
```
parse_intent → generate_skeleton → confirm_skeleton → generate_agents → done
                                         ↓ [rejected]
                                    parse_intent
```

## Tool Extensions

New tools needed in `core/tools.py`:
1. `write_file(file_path, content)` - Write generated files
2. `read_file(file_path)` - Read files for processing

## Implementation Phases

### Phase 1: Core Tools
- Add file I/O tools to ToolRegistry
- Test with real DeepSeek LLM

### Phase 2: Intent Parser
- Create intent_parser agent
- Test output format compliance
- Fix prompt issues (condition format)

### Phase 3: Skeleton Builder
- Create skeleton_builder agent
- Generate valid flow.md
- Test with various workflow types

### Phase 4: Agent Builder
- Create agent_builder agent
- Generate agent.md for each node
- Test memory strategy inference

### Phase 5: Integration Testing
- End-to-end workflow generation
- Test cases: simple, loop, conditional, multi-path
- Validate generated workflows execute correctly

## Known Issues
1. Intent parser outputs conditions without `[brackets]` format
2. Need to ensure generated files are parseable by existing parser

## Success Criteria
- User provides intent → system generates executable workflow
- Generated workflows pass all existing tests
- Support loops, conditionals, multiple paths
