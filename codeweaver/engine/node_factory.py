from typing import Callable
import json
import logging
from codeweaver.parser.agent import AgentDef
from codeweaver.memory.manager import MemoryManager
from codeweaver.tools.executor import ToolExecutor

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
MAX_TOOL_ITERATIONS = 5


def make_node(
    agent_def: AgentDef,
    memory: MemoryManager,
    total_steps: int,
    llm_fn: Callable | None = None,
    step_goal: str = "",
    step_raw_text: str = "",
    project_root: str = ".",
) -> Callable:
    """Returns a LangGraph node function for the given agent.

    Args:
        agent_def: The agent definition containing system prompt and model config
        memory: Memory manager for loading/writing agent context
        total_steps: Total number of steps in the workflow
        llm_fn: Optional custom LLM function for testing/mocking
        step_goal: High-level goal for the current step (from orchestrator)
        step_raw_text: Raw markdown text from workflow definition (user instructions)
        project_root: Root directory for tool execution sandboxing

    Returns:
        A callable node function compatible with LangGraph
    """

    def node(state: dict) -> dict:
        bundle = memory.load_agent_memory_bundle(
            agent_def.name, state["current_step"], total_steps
        )

        # Build structured context with step information
        context_parts = []
        # Include step context if either goal or raw_text is provided
        if step_goal or step_raw_text:
            context_parts.append("# Current Step Context")
            if step_goal:
                context_parts.append(f"**Goal:** {step_goal}")
            if step_raw_text:
                context_parts.append(f"**Instructions:**\n{step_raw_text}")
            context_parts.append("")

        context_parts.append("# Memory Context")
        context_parts.append(bundle)

        if state.get("task_description"):
            context_parts.append(f"\n\nTask: {state['task_description']}")

        user_content = "\n".join(context_parts)

        messages = [
            {"role": "system", "content": agent_def.system_prompt},
            {"role": "user", "content": user_content},
        ]

        # Initialize tool executor if agent has tools
        tool_executor = None
        tool_schemas = None
        if agent_def.tools:
            tool_executor = ToolExecutor(project_root)
            tool_schemas = tool_executor.get_tool_schemas()
            logger.info(f"Agent {agent_def.name} initialized with {len(tool_schemas)} tools")

        # Tool execution loop
        response = None
        for iteration in range(MAX_TOOL_ITERATIONS):
            logger.debug(f"Tool iteration {iteration + 1}/{MAX_TOOL_ITERATIONS}")

            # Call LLM with tool schemas if available
            if llm_fn is not None:
                if tool_schemas:
                    response = llm_fn(messages, tools=tool_schemas)
                else:
                    response = llm_fn(messages)
            else:
                import litellm
                if tool_schemas:
                    resp = litellm.completion(
                        model=agent_def.model or "gpt-4o",
                        messages=messages,
                        tools=tool_schemas
                    )
                else:
                    resp = litellm.completion(
                        model=agent_def.model or "gpt-4o",
                        messages=messages
                    )
                response = resp.choices[0].message

            # Handle string response (backward compatibility)
            if isinstance(response, str):
                logger.debug("LLM returned string response (no tool calls)")
                memory.write_agent_context(agent_def.name, response)
                return {**state, "status": "running", "current_step": state["current_step"]}

            # Handle dict response with potential tool calls
            tool_calls = None
            if isinstance(response, dict):
                tool_calls = response.get("tool_calls")
                content = response.get("content")
            else:
                # litellm response object
                tool_calls = getattr(response, "tool_calls", None)
                content = getattr(response, "content", None)

            # If no tool calls, we're done
            if not tool_calls:
                logger.debug("No tool calls in response, completing")
                final_content = content if content else str(response)
                memory.write_agent_context(agent_def.name, final_content)
                return {**state, "status": "running", "current_step": state["current_step"]}

            # Execute tool calls
            logger.info(f"Executing {len(tool_calls)} tool call(s)")

            # Add assistant message with tool calls to conversation
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls if isinstance(tool_calls, list) else [tool_calls]
            })

            # Execute each tool and add results
            for tool_call in (tool_calls if isinstance(tool_calls, list) else [tool_calls]):
                tool_call_id = tool_call.get("id", "unknown")
                function_data = tool_call.get("function", {})
                tool_name = function_data.get("name")
                arguments_str = function_data.get("arguments", "{}")

                logger.debug(f"Executing tool: {tool_name}")

                try:
                    # Parse arguments
                    arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str

                    # Execute tool
                    result = tool_executor.execute(tool_name, **arguments)

                    # Format result for LLM
                    if result.success:
                        result_content = json.dumps({
                            "success": True,
                            "output": result.output
                        })
                    else:
                        result_content = json.dumps({
                            "success": False,
                            "error": result.error
                        })

                    logger.debug(f"Tool {tool_name} executed: success={result.success}")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool arguments: {e}")
                    result_content = json.dumps({
                        "success": False,
                        "error": f"Invalid arguments format: {str(e)}"
                    })
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}", exc_info=True)
                    result_content = json.dumps({
                        "success": False,
                        "error": str(e)
                    })

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result_content
                })

        # If we hit max iterations, use last response
        logger.warning(f"Reached MAX_TOOL_ITERATIONS ({MAX_TOOL_ITERATIONS})")
        final_content = "Maximum tool iterations reached"
        if isinstance(response, dict):
            final_content = response.get("content", final_content)
        elif hasattr(response, "content"):
            final_content = response.content or final_content

        memory.write_agent_context(agent_def.name, final_content)
        return {**state, "status": "running", "current_step": state["current_step"]}

    return node
