from pathlib import Path
from codeweaver.generator.analyzer import WorkflowAnalyzer
from codeweaver.generator.agent_gen import generate_agent
from codeweaver.parser.workflow import parse_workflow
from codeweaver.parser.agent import load_agent_registry

FIXTURE = Path(__file__).parent / "fixtures" / "slow_sort_project"

def make_mock_llm(goal_prefix="Perform task", capability="general", match="NONE"):
    """Returns deterministic mock LLM for analysis."""
    call_count = [0]
    def llm_fn(messages):
        call_count[0] += 1
        content = messages[-1]["content"].lower()
        if "one sentence" in content or "goal" in content:
            return f"{goal_prefix} for step {call_count[0]}"
        if "capability" in content or "required" in content:
            return capability
        if "which agent" in content or "matches" in content:
            return match
        return goal_prefix
    return llm_fn

def test_analyze_slow_sort_project(tmp_path):
    """Full analysis of slow_sort_project/optimizer.md with mock LLM."""
    wf_text = (FIXTURE / "optimizer.md").read_text()
    wf = parse_workflow(wf_text)
    assert wf.name == "slow-sort-optimizer"
    assert len(wf.steps) == 5

    # Workflow has explicit @agent annotations for steps 1, 3, 4
    # Steps 2, 5 have no explicit agents → gaps
    registry = {}
    llm = make_mock_llm()
    analyzer = WorkflowAnalyzer(registry=registry, llm_fn=llm)
    tree = analyzer.analyze(wf)

    assert len(tree.steps) == 5
    assert len(tree.gaps) == 2  # steps 2 and 5 are gaps
    md = tree.to_markdown()
    assert "slow-sort-optimizer" in md
    assert "MISSING ✗" in md

def test_generate_agents_for_gaps(tmp_path):
    """Generate agent YAMLs for all gaps in slow_sort_project."""
    wf_text = (FIXTURE / "optimizer.md").read_text()
    wf = parse_workflow(wf_text)
    registry = {}
    llm = make_mock_llm()
    analyzer = WorkflowAnalyzer(registry=registry, llm_fn=llm)
    tree = analyzer.analyze(wf)

    # Mock LLM that returns different agent names for each call
    call_count = [0]
    def gen_llm(msgs):
        call_count[0] += 1
        name = f"gap-agent-{call_count[0]}"
        return f"""
```yaml
name: {name}
description: Handles gap {call_count[0]}
system_prompt: You handle gap {call_count[0]}.
tools:
  - run_command
```
"""
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    generated = []
    for gap in tree.gaps[:2]:  # generate first 2
        agent = generate_agent(gap, gen_llm, agents_dir)
        generated.append(agent)

    assert len(generated) == 2
    assert len(list(agents_dir.glob("*.yaml"))) == 2

def test_analysis_tree_markdown_structure(tmp_path):
    """Verify the markdown tree has correct hierarchical structure."""
    wf_text = (FIXTURE / "optimizer.md").read_text()
    wf = parse_workflow(wf_text)
    llm = make_mock_llm(goal_prefix="Execute task", capability="execution")
    analyzer = WorkflowAnalyzer(registry={}, llm_fn=llm)
    tree = analyzer.analyze(wf)
    md = tree.to_markdown()

    # Verify tree structure
    assert "## Meta" in md
    assert "## Step Tree" in md
    assert "### Step 1:" in md
    assert "- Goal:" in md
    assert "- Required capability:" in md
    assert "- Matched agent:" in md
