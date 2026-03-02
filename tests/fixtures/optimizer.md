---
name: optimizer
description: Optimize a Python algorithm for performance
entry_command: python src/main.py
---

## Step 1: Analyze Structure
@structure-agent: Read the project and map the overall architecture

## Step 2 (parallel): Identify Entry Point
### Step 2a: List Files
@interact-agent: Identify the project entry file
@tool:select: Present file options to user

### Step 2b: Analyze Dependencies
Analyze import relationships between files

## Step 3: Identify Target Algorithm
Ask user which algorithm to optimize and define the goal

## Step 4: Establish Baseline
@runner-agent: Execute the entry command and save output

## Step 5: Optimize
@coder-agent: Optimize the target algorithm

## Step 6: Validate
@validator-agent: Re-run entry command, compare output against baseline
