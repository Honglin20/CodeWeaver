from typing import Callable
import json
import logging
from rich.console import Console
from codeweaver.parser.agent import AgentDef
from codeweaver.memory.manager import MemoryManager
from codeweaver.tools.executor import ToolExecutor
from codeweaver.engine.context_builder import ContextBuilder

logger = logging.getLogger(__name__)
console = Console()

MAX_RETRIES = 3
MAX_TOOL_ITERATIONS = 10


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
        # Build context using ContextBuilder
        context_builder = ContextBuilder()
        messages = context_builder.build_messages(
            agent_def, memory, state, total_steps, step_goal, step_raw_text
        )

        # Initialize tool executor if agent has tools
        tool_executor = None
        tool_schemas = None
        allowed_tools = set(agent_def.tools) if agent_def.tools else set()
        if agent_def.tools:
            tool_executor = ToolExecutor(project_root)
            # Filter tool schemas to only include allowed tools
            all_schemas = tool_executor.get_tool_schemas()
            tool_schemas = [
                schema for schema in all_schemas
                if schema["function"]["name"] in allowed_tools
            ]
            logger.info(f"Agent {agent_def.name} initialized with {len(tool_schemas)} tools: {allowed_tools}")

        # Tool execution loop
        response = None
        executed_tools = []  # Track tools called for error reporting
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

            # Keep conversation history manageable to avoid token limits
            # Keep system message + user message + recent tool exchanges
            # More aggressive truncation to stay well under 8K token limit
            if len(messages) > 8:
                # Always keep: system (0), user (1)
                # Keep last 5 messages (should be ~1 complete tool exchange)
                messages = messages[:2] + messages[-5:]

            # Execute each tool and add results
            for tool_call in (tool_calls if isinstance(tool_calls, list) else [tool_calls]):
                tool_call_id = tool_call.get("id", "unknown")
                function_data = tool_call.get("function", {})
                tool_name = function_data.get("name")
                arguments_str = function_data.get("arguments", "{}")

                logger.debug(f"Executing tool: {tool_name}")

                # Display tool execution to user
                args_preview = str(arguments_str)[:50] + "..." if len(str(arguments_str)) > 50 else str(arguments_str)
                console.print(f"  [dim]→ Calling {tool_name}({args_preview})[/dim]")

                # Validate tool is in agent's allowed tools list
                if tool_name not in allowed_tools:
                    logger.warning(f"Agent {agent_def.name} attempted to call unauthorized tool: {tool_name}")
                    result_content = json.dumps({
                        "success": False,
                        "error": f"Tool '{tool_name}' is not in the allowed tools list for this agent"
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_content
                    })
                    continue

                # Track executed tool for error reporting
                executed_tools.append(tool_name)

                try:
                    # Parse arguments
                    arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str

                    # Execute tool
                    result = tool_executor.execute(tool_name, **arguments)

                    # Format result for LLM with safe JSON serialization
                    try:
                        if result.success:
                            result_content = json.dumps({
                                "success": True,
                                "output": result.output
                            })
                            console.print(f"  [dim green]✓ {tool_name} succeeded[/dim green]")
                        else:
                            result_content = json.dumps({
                                "success": False,
                                "error": result.error
                            })
                            console.print(f"  [yellow]⚠ {tool_name} failed: {result.error}[/yellow]")
                    except (TypeError, ValueError) as e:
                        # Handle non-serializable objects
                        logger.warning(f"Tool result not JSON serializable, converting to string: {e}")
                        if result.success:
                            result_content = json.dumps({
                                "success": True,
                                "output": str(result.output)
                            })
                            console.print(f"  [dim green]✓ {tool_name} succeeded[/dim green]")
                        else:
                            result_content = json.dumps({
                                "success": False,
                                "error": str(result.error)
                            })
                            console.print(f"  [yellow]⚠ {tool_name} failed: {str(result.error)}[/yellow]")

                    logger.debug(f"Tool {tool_name} executed: success={result.success}")

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse tool arguments: {e}")
                    console.print(f"  [red]✗ {tool_name} - Invalid arguments: {str(e)}[/red]")
                    result_content = json.dumps({
                        "success": False,
                        "error": f"Invalid arguments format: {str(e)}"
                    })
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}", exc_info=True)
                    console.print(f"  [red]✗ {tool_name} - Execution error: {str(e)}[/red]")
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
        logger.warning(
            f"Reached MAX_TOOL_ITERATIONS ({MAX_TOOL_ITERATIONS}). "
            f"Tools called: {executed_tools}"
        )
        final_content = f"Maximum tool iterations reached. Tools executed: {', '.join(executed_tools)}"
        if isinstance(response, dict):
            content = response.get("content")
            if content:
                final_content = f"{content}\n\n{final_content}"
        elif hasattr(response, "content") and response.content:
            final_content = f"{response.content}\n\n{final_content}"

        memory.write_agent_context(agent_def.name, final_content)
        return {**state, "status": "running", "current_step": state["current_step"]}

    return node
