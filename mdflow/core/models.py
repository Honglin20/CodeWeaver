"""Pydantic data models for configuration validation."""
from typing import List, Optional
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Agent configuration from markdown file."""
    name: str
    model: str
    max_output_tokens: int = Field(default=2000, gt=0)
    memory_strategy: str = "full"
    tools: List[str] = Field(default_factory=list)
    system_prompt: str = ""


class WorkflowNode(BaseModel):
    """Workflow node definition."""
    name: str
    agent_name: str
    description: Optional[str] = None


class WorkflowEdge(BaseModel):
    """Workflow edge with routing condition."""
    source: str
    target: str
    condition: Optional[str] = None


class WorkflowConfig(BaseModel):
    """Workflow configuration from markdown file."""
    workflow_name: str
    entry_point: str
    end_point: str
    nodes: List[WorkflowNode] = Field(default_factory=list)
    edges: List[WorkflowEdge] = Field(default_factory=list)
