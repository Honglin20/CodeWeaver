from codeweaver.generator.reviewer import review_agents
from codeweaver.parser.agent import AgentDef

def make_agent(name="test-agent"):
    return AgentDef(
        name=name, description="A test agent",
        system_prompt="You are a test agent.",
        tools=["read_file"],
    )

def test_accept_all_agents(tmp_path):
    agents = [make_agent("agent-a"), make_agent("agent-b")]
    prompt_fn = lambda q, choices: "accept"
    accepted = review_agents(agents, tmp_path, prompt_fn=prompt_fn)
    assert len(accepted) == 2
    assert (tmp_path / "agent-a.yaml").exists()
    assert (tmp_path / "agent-b.yaml").exists()

def test_skip_agent_not_written(tmp_path):
    agents = [make_agent("agent-a")]
    prompt_fn = lambda q, choices: "skip"
    accepted = review_agents(agents, tmp_path, prompt_fn=prompt_fn)
    assert len(accepted) == 0
    assert not (tmp_path / "agent-a.yaml").exists()

def test_mixed_accept_skip(tmp_path):
    agents = [make_agent("agent-a"), make_agent("agent-b")]
    responses = ["accept", "skip"]
    prompt_fn = lambda q, choices: responses.pop(0)
    accepted = review_agents(agents, tmp_path, prompt_fn=prompt_fn)
    assert len(accepted) == 1
    assert accepted[0].name == "agent-a"
