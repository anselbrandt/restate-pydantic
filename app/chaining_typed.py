from typing import Optional, List
import restate
from pydantic_ai import Agent, FunctionToolset
from pydantic import BaseModel
from restate import RunOptions, TerminalError


def llm_call(
    prompt: str,
    system: str = "",
    messages: Optional[list[dict[str, str]]] = [],
    tools: Optional[List] = [],
) -> str:

    if not prompt and not messages:
        raise TerminalError("Either prompt or messages must be provided.")

    agent = Agent(model="openai:gpt-4o", system_prompt=system)
    toolsets = [FunctionToolset(tools=list(tools))] if tools else []
    result = agent.run_sync(
        user_prompt=prompt,
        message_history=messages,
        toolsets=toolsets,
    )

    if result.output:
        return result.output
    else:
        raise RuntimeError("No content in response")


call_chaining_svc_typed = restate.Service("CallChainingService_typed")

example_prompt = """Q3 Performance Summary:
Our customer satisfaction score rose to 92 points this quarter.
Revenue grew by 45% compared to last year.
Market share is now at 23% in our primary market.
Customer churn decreased to 5% from 8%."""


class Prompt(BaseModel):
    message: str = example_prompt


@call_chaining_svc_typed.handler()
async def run(ctx: restate.Context, prompt: Prompt) -> str:
    """Chains multiple LLM calls sequentially, where each step processes the previous step's output."""

    # Step 1: Process the initial input with the first prompt
    result = await ctx.run_typed(
        "Extract metrics",
        llm_call,
        RunOptions(max_attempts=3),
        prompt=f"Extract only the numerical values and their associated metrics from the text. "
        f"Format each as 'metric name: metric' on a new line. Input: {prompt.message}",
    )

    # Step 2: Process the result from Step 1
    result2 = await ctx.run_typed(
        "Sort metrics",
        llm_call,
        RunOptions(max_attempts=3),
        prompt=f"Sort all lines in descending order by numerical value. Input: {result}",
    )

    # Step 3: Process the result from Step 2
    result3 = await ctx.run_typed(
        "Format as table",
        llm_call,
        RunOptions(max_attempts=3),
        prompt=f"Format the sorted data as a markdown table with columns 'Metric Name' and 'Value'. Input: {result2}",
    )

    return result3
