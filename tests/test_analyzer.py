# tests/test_analyzer.py
from codeweaver.generator.analyzer import WorkflowAnalyzer, AnalysisTree, StepAnalysis
from codeweaver.parser.workflow import WorkflowDef, StepDef
from codeweaver.parser.agent import AgentDef

def make_registry():
    return {
        "structure-agent": AgentDef(
            name="structure-agent",
            description="Analyzes Python project structure",
            system_prompt="You analyze code structure.",
        )
    }

def make_llm(responses: list[str]):
    """Returns a mock llm_fn that pops responses in order."""
    responses = list(responses)
    def llm_fn(messages):
        return responses.pop(0)
    return llm_fn

def test_matched_agent_no_gap():
    wf = WorkflowDef(name="test", description="test", entry_command=None, steps=[
        StepDef(index=0, title="Analyze Structure", raw_text="@structure-agent: analyze",
                explicit_agents=["structure-agent"], explicit_tools=[], parallel=False, sub_steps=[])
    ])
    llm = make_llm(["Understand project architecture", "code analysis", "structure-agent"])
    analyzer = WorkflowAnalyzer(registry=make_registry(), llm_fn=llm)
    tree = analyzer.analyze(wf)
    assert tree.steps[0].matched_agent == "structure-agent"
    assert tree.steps[0].gap == False
    assert len(tree.gaps) == 0

def test_missing_agent_creates_gap():
    wf = WorkflowDef(name="test", description="test", entry_command=None, steps=[
        StepDef(index=0, title="Validate Results", raw_text="validate output",
                explicit_agents=[], explicit_tools=[], parallel=False, sub_steps=[])
    ])
    llm = make_llm(["Verify optimization correctness", "output validation", "NONE"])
    analyzer = WorkflowAnalyzer(registry=make_registry(), llm_fn=llm)
    tree = analyzer.analyze(wf)
    assert tree.steps[0].matched_agent is None
    assert tree.steps[0].gap == True
    assert len(tree.gaps) == 1

def test_explicit_agent_skips_llm_matching():
    """If step has explicit_agents, use it directly — no LLM call for matching."""
    call_count = [0]
    def counting_llm(messages):
        call_count[0] += 1
        return "Understand structure"  # only goal extraction calls
    wf = WorkflowDef(name="test", description="test", entry_command=None, steps=[
        StepDef(index=0, title="Step 1", raw_text="@structure-agent: do it",
                explicit_agents=["structure-agent"], explicit_tools=[], parallel=False, sub_steps=[])
    ])
    analyzer = WorkflowAnalyzer(registry=make_registry(), llm_fn=counting_llm)
    tree = analyzer.analyze(wf)
    assert tree.steps[0].matched_agent == "structure-agent"
    # LLM called for goal + capability, but NOT for agent matching (explicit)
    assert call_count[0] <= 2

def test_analysis_tree_to_markdown():
    tree = AnalysisTree(
        workflow_name="optimizer",
        workflow_description="Optimize algorithm",
        steps=[
            StepAnalysis(0, "Analyze", "Understand structure", "code analysis", "structure-agent", False),
            StepAnalysis(1, "Validate", "Verify results", "output validation", None, True),
        ]
    )
    md = tree.to_markdown()
    assert "# Workflow Analysis: optimizer" in md
    assert "structure-agent ✓" in md
    assert "MISSING ✗" in md
    assert "Gaps found: 1" in md

def test_multiple_steps_dependency_order():
    """Steps analyzed in order, gaps list preserves order."""
    wf = WorkflowDef(name="test", description="test", entry_command=None, steps=[
        StepDef(index=0, title="Step A", raw_text="analyze", explicit_agents=[], explicit_tools=[], parallel=False, sub_steps=[]),
        StepDef(index=1, title="Step B", raw_text="validate", explicit_agents=[], explicit_tools=[], parallel=False, sub_steps=[]),
    ])
    llm = make_llm(["goal A", "cap A", "NONE", "goal B", "cap B", "NONE"])
    analyzer = WorkflowAnalyzer(registry={}, llm_fn=llm)
    tree = analyzer.analyze(wf)
    assert len(tree.gaps) == 2
    assert tree.gaps[0].step_index == 0
    assert tree.gaps[1].step_index == 1
