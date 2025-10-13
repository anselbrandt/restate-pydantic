from typing import Optional, List

from dotenv import load_dotenv
from pydantic_ai import Agent, FunctionToolset
from restate import TerminalError
import logfire

load_dotenv()

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()


def llm_call(
    prompt: str,
    system: str = "",
    messages: Optional[list[dict[str, str]]] = [],
    tools: Optional[List] = [],
) -> str:
    """
    Calls the model with the given prompt and returns the response.

    Args:
        prompt (str): The user prompt to send to the model.
        system (str, optional): The system prompt to send to the model. Defaults to "".
        messages (list, optional): Previous messages for context in chat models. Defaults to None.
        tools (list, optional): List of tools for the model to use. Defaults to None.

    Returns:
        str: The response from the language model.
    """

    if not prompt and not messages:
        raise TerminalError("Either prompt or messages must be provided.")

    agent = Agent(model="openai:gpt-4o", system_prompt=system)
    result = agent.run_sync(
        user_prompt=prompt,
        message_history=messages,
        toolsets=[FunctionToolset(tools=tools)],
    )

    if result.output:
        return result.output
    else:
        raise RuntimeError("No content in response")
