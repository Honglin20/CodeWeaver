"""
Interactive tool handlers for user prompts and selections.

This module provides handlers for interactive tools that pause workflow
execution and wait for user input using LangGraph interrupts.
"""

from langgraph.types import Command


class InteractiveToolHandler:
    """
    Handler for interactive tools that require user input.

    Interactive tools use LangGraph Command with interrupts to pause
    workflow execution and wait for user responses.
    """

    def handle_select(self, prompt: str, options: list[str]) -> Command:
        """
        Create an interrupt for user to select from options.

        Args:
            prompt: The question or prompt to show the user
            options: List of options to choose from (minimum 2 required)

        Returns:
            Command with interrupt data for LangGraph

        Raises:
            ValueError: If prompt is empty or less than 2 options provided
            TypeError: If options are not all strings
        """
        # Validate prompt
        if not prompt or not prompt.strip():
            raise ValueError("prompt cannot be empty")

        # Validate options count
        if len(options) < 2:
            raise ValueError("tool_select requires at least 2 options")

        # Validate option types
        if not all(isinstance(opt, str) for opt in options):
            raise TypeError("All options must be strings")

        # Create interrupt data
        interrupt_data = {
            "type": "select",
            "prompt": prompt,
            "options": options
        }

        # Return Command with interrupt
        return Command(
            graph=Command.PARENT,
            update={"__interrupt__": interrupt_data}
        )
