# Optimizer Workflow Guide

## Overview

The optimizer workflow demonstrates CodeWeaver's multi-agent coordination capabilities through a complete algorithm optimization pipeline. It combines user interaction, code analysis, optimization, and validation into a single automated workflow.

**Key Features:**
- Interactive user guidance via `@interact-agent`
- Automated baseline/optimized output comparison
- Correctness validation with automatic bug-fix loops
- Performance measurement and reporting

## The 8-Step Process

### Step 1: Analyze Project Structure
```markdown
@structure-agent: Read the project and understand the overall architecture.
Output the file structure and key components.
```

The structure-agent scans the project directory and creates a hierarchical map of files, identifying Python modules, entry points, and key components.

**Output:** `.codeweaver/memory/agents/structure-agent/context.md`

### Step 2: Identify Entry Point
```markdown
@interact-agent: Present the list of Python files to the user.
@tool:select: Let user confirm the entry file.
Save the user's choice to memory.
```

The interact-agent presents discovered Python files to the user via an interactive selection prompt. The user confirms which file serves as the program's entry point.

**User Interaction:** Multiple-choice selection
**Output:** Saved to interact-agent's memory

### Step 3: Ask Optimization Target
```markdown
@interact-agent: Ask the user which file contains the algorithm to optimize.
Ask what the optimization goal is (speed, memory, etc.).
Save responses to memory.
```

The interact-agent asks two critical questions:
1. Which file contains the algorithm to optimize?
2. What is the optimization goal? (speed, memory, readability, etc.)

**User Interaction:** Text input or selection
**Output:** Saved to interact-agent's memory

### Step 4: Identify Specific Algorithm
```markdown
@interact-agent: Query @structure-agent for functions/classes in target file.
@tool:select: Present list of functions to user.
Confirm which specific function to optimize.
Save selection to memory.
```

The interact-agent coordinates with structure-agent to extract all functions/classes from the target file, then presents them to the user for selection.

**User Interaction:** Multiple-choice selection
**Output:** Saved to interact-agent's memory

### Step 5: Save User Choices
```markdown
@interact-agent: Write all user selections to agents/interact-agent/choices.md:
- Entry file
- Target file
- Target function
- Optimization goal
```

All user choices are consolidated into a single markdown file for downstream agents to reference.

**Output:** `.codeweaver/memory/agents/interact-agent/choices.md`

Example:
```markdown
# User Choices

- **Entry file:** src/main.py
- **Target file:** src/sorter.py
- **Target function:** bubble_sort
- **Optimization goal:** speed
```

### Step 6: Run Baseline
```markdown
@interact-agent: Execute entry_command and capture output.
Save output to memory/baseline_output.md.
Record execution time and any metrics.
```

The interact-agent executes the entry command (defined in workflow frontmatter) and captures:
- Standard output
- Execution time
- Result hash (for correctness verification)

**Output:** `.codeweaver/memory/baseline_output.md`

Example:
```markdown
# Baseline Output

**Execution Time:** 0.1234s
**Result Hash:** abc12345def67890

Sorted array: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
```

### Step 7: Optimize Algorithm
```markdown
@coder-agent: Read target file and function from memory.
Apply optimization based on user's goal.
Use @tool:edit_code to modify the file.
Re-run entry_command and save output to memory/optimized_output.md.
```

The coder-agent:
1. Reads the target file and function from interact-agent's choices
2. Applies optimization techniques based on the goal (e.g., replace bubble sort with quicksort)
3. Uses `@tool:edit_code` to modify the source file
4. Re-runs the entry command
5. Captures optimized output with timing and hash

**Output:** `.codeweaver/memory/optimized_output.md`

Example:
```markdown
# Optimized Output

**Execution Time:** 0.0056s
**Result Hash:** abc12345def67890

Sorted array: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
```

### Step 8 (loop): Validate Optimization
```markdown
@validator-agent: Compare baseline_output.md vs optimized_output.md.
Check if outputs match (correctness).
Check if optimization goal met (speed/memory improvement).
If bugs detected: @coder-agent fixes, return to Step 7.
If validation passes: Report success and metrics.
```

The validator-agent performs three checks:

1. **Correctness:** Compare result hashes (baseline vs optimized)
2. **Performance:** Verify improvement meets optimization goal
3. **Regression Detection:** Identify any unexpected behavior

**Validation Outcomes:**

- ✅ **Pass:** Outputs match, performance improved → Report success
- ❌ **Fail:** Outputs differ or performance regressed → Trigger bug-fix loop

**Bug-Fix Loop:**
If validation fails, the validator-agent sets `status="error"` and provides diagnostic information. The workflow automatically returns to Step 7, where coder-agent attempts to fix the issue.

**Output:** `.codeweaver/memory/agents/validator-agent/context.md`

Example (success):
```markdown
# Validation Report

**Status:** ✅ PASS

**Correctness:** Outputs match (hash: abc12345def67890)
**Performance:** 22x speedup (0.1234s → 0.0056s)
**Optimization Goal:** speed ✅ MET

The optimization successfully improved performance while maintaining correctness.
```

Example (failure):
```markdown
# Validation Report

**Status:** ❌ FAIL

**Correctness:** ❌ Outputs differ
- Baseline hash: abc12345def67890
- Optimized hash: xyz98765fed43210

**Issue:** Optimized algorithm produces incorrect results.
**Action:** Triggering bug-fix loop (return to Step 7).
```

## Agent Roles

### interact-agent
**Purpose:** Coordinate user interaction and capture choices

**Capabilities:**
- Present interactive prompts via `@tool:select`
- Execute commands and capture output
- Write user choices to memory for downstream agents
- Measure execution time and compute result hashes

**Memory:**
- Writes: `agents/interact-agent/choices.md`, `memory/baseline_output.md`, `memory/optimized_output.md`
- Reads: Structure-agent's output

### validator-agent
**Purpose:** Ensure optimization correctness and performance

**Capabilities:**
- Compare baseline vs optimized outputs
- Verify result hashes match (correctness)
- Measure performance improvements
- Detect bugs and trigger fix loops

**Memory:**
- Reads: `memory/baseline_output.md`, `memory/optimized_output.md`, `agents/interact-agent/choices.md`
- Writes: `agents/validator-agent/context.md`

**Validation Logic:**
```python
# Pseudocode
baseline = read_baseline_output()
optimized = read_optimized_output()

if baseline.result_hash != optimized.result_hash:
    return status="error", message="Outputs differ"

if optimized.execution_time >= baseline.execution_time:
    return status="error", message="No performance improvement"

return status="success", improvement=baseline.time / optimized.time
```

## Customization

### Adapting for Different Optimization Goals

The workflow supports multiple optimization goals:

**Speed Optimization:**
```markdown
## Step 3: Ask Optimization Target
@interact-agent: Ask what the optimization goal is.
Options: ["speed", "memory", "readability"]
```

**Memory Optimization:**
- Validator checks memory usage instead of execution time
- Requires memory profiling tools (e.g., `memory_profiler`)

**Readability Optimization:**
- Validator checks code complexity metrics (e.g., cyclomatic complexity)
- May skip performance comparison

### Custom Validation Criteria

Modify `validator-agent.yaml` to add custom checks:

```yaml
system_prompt: |
  Additional validation criteria:
  - Check if code follows PEP 8 style guide
  - Verify type hints are present
  - Ensure docstrings are added
```

### Multi-File Optimizations

For optimizations spanning multiple files:

```markdown
## Step 3: Ask Optimization Target
@interact-agent: Ask which files contain the algorithm to optimize.
@tool:select: Allow multiple file selection.
```

## Example Walkthrough

### Scenario: Optimizing slow_sort_project

**Project Structure:**
```
slow_sort_project/
├── src/
│   ├── main.py       # Entry point
│   ├── sorter.py     # Contains bubble_sort
│   └── utils.py      # Helper functions
└── optimizer.md      # Workflow definition
```

**Step-by-Step Execution:**

1. **Run workflow:**
   ```bash
   cd tests/fixtures/slow_sort_project
   codeweaver run optimizer.md
   ```

2. **Step 1-2:** Structure analysis and entry point selection
   ```
   [structure-agent] Analyzing project...
   [interact-agent] Select entry file:
   > src/main.py
     src/sorter.py
     src/utils.py
   ```

3. **Step 3-4:** Target selection
   ```
   [interact-agent] Which file contains the algorithm to optimize?
   > src/sorter.py

   [interact-agent] What is the optimization goal?
   > speed

   [interact-agent] Select function to optimize:
   > bubble_sort
     quick_sort
     merge_sort
   ```

4. **Step 5:** Choices saved to memory
   ```
   [interact-agent] Saved choices to agents/interact-agent/choices.md
   ```

5. **Step 6:** Baseline execution
   ```
   [interact-agent] Running baseline...
   Execution time: 0.1234s
   Result hash: abc12345def67890
   ```

6. **Step 7:** Optimization
   ```
   [coder-agent] Reading target function: bubble_sort
   [coder-agent] Applying speed optimization...
   [coder-agent] Replacing bubble_sort with quicksort
   [coder-agent] Running optimized version...
   Execution time: 0.0056s
   Result hash: abc12345def67890
   ```

7. **Step 8:** Validation
   ```
   [validator-agent] Comparing outputs...
   ✅ Correctness: PASS (hashes match)
   ✅ Performance: 22x speedup
   ✅ Optimization goal: MET

   Validation successful!
   ```

**Final Output:**
```
Optimization complete!
- Baseline: 0.1234s
- Optimized: 0.0056s
- Improvement: 22x faster
- Correctness: ✅ Verified
```

## Troubleshooting

### Issue: Validation fails with "Outputs differ"

**Cause:** Optimized algorithm produces incorrect results

**Solution:**
1. Check `.codeweaver/memory/agents/validator-agent/context.md` for diagnostic info
2. Review coder-agent's changes in git diff
3. The workflow will automatically trigger bug-fix loop
4. If loop fails repeatedly, manually inspect the optimized code

### Issue: No performance improvement detected

**Cause:** Optimization didn't improve performance or made it worse

**Solution:**
1. Check if optimization goal matches the algorithm's bottleneck
2. Review coder-agent's optimization strategy
3. Consider different optimization techniques (e.g., algorithmic vs micro-optimizations)

### Issue: interact-agent doesn't present options

**Cause:** structure-agent failed to analyze project

**Solution:**
1. Check `.codeweaver/memory/agents/structure-agent/context.md`
2. Verify project structure is valid Python
3. Ensure entry_command in workflow frontmatter is correct

### Issue: Workflow hangs at @tool:select

**Cause:** Interactive prompt waiting for user input

**Solution:**
1. Check terminal for prompt
2. Ensure `prompt_toolkit` is installed
3. Verify terminal supports interactive input

### Issue: Memory files not created

**Cause:** Memory system not initialized

**Solution:**
1. Ensure `.codeweaver/memory/` directory exists
2. Check file permissions
3. Verify memory manager is configured in workflow engine

## Advanced Topics

### Parallel Validation

For large projects, run multiple optimizations in parallel:

```markdown
## Step 7: Optimize Multiple Functions
@coder-agent[1]: Optimize function_a
@coder-agent[2]: Optimize function_b
@coder-agent[3]: Optimize function_c

## Step 8: Validate All
@validator-agent: Compare all baseline/optimized pairs
```

### Incremental Optimization

Apply optimizations iteratively:

```markdown
## Step 7 (loop): Incremental Optimization
@coder-agent: Apply one optimization technique
@validator-agent: Validate improvement
If improvement < 10%: Try next technique
If improvement >= 10%: Accept and continue
```

### Custom Metrics

Add custom performance metrics:

```yaml
# validator-agent.yaml
system_prompt: |
  Custom metrics to track:
  - CPU cycles (via perf)
  - Cache misses
  - Memory allocations
  - I/O operations
```

## Conclusion

The optimizer workflow demonstrates CodeWeaver's ability to orchestrate complex multi-agent tasks with user interaction, validation, and automatic error recovery. By combining declarative workflow definitions with intelligent agents, it provides a powerful framework for automated code optimization.

For more examples, see:
- `tests/fixtures/slow_sort_project/` — Complete working example
- `tests/fixtures/agents/` — Agent definitions
- `docs/design.md` — Architecture details
