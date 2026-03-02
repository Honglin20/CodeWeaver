---
name: optimizer
description: Optimize a Python algorithm with user guidance and validation
entry_command: python src/main.py
---

## Step 1: Analyze Project Structure
@structure-agent: Read the project and understand the overall architecture.
Output the file structure and key components.

## Step 2: Identify Entry Point
@interact-agent: Present the list of Python files to the user.
@tool:select: Let user confirm the entry file.
Save the user's choice to memory.

## Step 3: Ask Optimization Target
@interact-agent: Ask the user which file contains the algorithm to optimize.
Ask what the optimization goal is (speed, memory, etc.).
Save responses to memory.

## Step 4: Identify Specific Algorithm
@interact-agent: Query @structure-agent for functions/classes in target file.
@tool:select: Present list of functions to user.
Confirm which specific function to optimize.
Save selection to memory.

## Step 5: Save User Choices
@interact-agent: Write all user selections to agents/interact-agent/choices.md:
- Entry file
- Target file
- Target function
- Optimization goal

## Step 6: Run Baseline
@interact-agent: Execute entry_command and capture output.
Save output to memory/baseline_output.md.
Record execution time and any metrics.

## Step 7: Optimize Algorithm
@coder-agent: Read target file and function from memory.
Apply optimization based on user's goal.
Use @tool:edit_code to modify the file.
Re-run entry_command and save output to memory/optimized_output.md.

## Step 8 (loop): Validate Optimization
@validator-agent: Compare baseline_output.md vs optimized_output.md.
Check if outputs match (correctness).
Check if optimization goal met (speed/memory improvement).
If bugs detected: @coder-agent fixes, return to Step 7.
If validation passes: Report success and metrics.
