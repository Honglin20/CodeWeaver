---
name: slow-sort-optimizer
description: Optimize the bubble sort algorithm in slow_sort_project
entry_command: python src/main.py
---

## Step 1: Analyze Structure
@structure-agent: Read the project and map the overall architecture

## Step 2: Identify Target
Ask user which algorithm to optimize

## Step 3: Establish Baseline
@runner-agent: Execute the entry command and save output as baseline

## Step 4: Optimize
@coder-agent: Replace bubble_sort with a faster implementation

## Step 5: Validate
Verify the optimized output matches baseline hash and runs faster
