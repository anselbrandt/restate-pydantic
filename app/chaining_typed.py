import restate
from pydantic_ai import Agent
from pydantic import BaseModel
from restate import RunOptions

from app.restate import RestateAgent


call_chaining_svc_typed = restate.Service("Call_Chaining_Service_Typed")

example_prompt = """Q3 Performance Summary:
Our customer satisfaction score rose to 92 points this quarter.
Revenue grew by 45% compared to last year.
Market share is now at 23% in our primary market.
Customer churn decreased to 5% from 8%."""


class Prompt(BaseModel):
    message: str = example_prompt


@call_chaining_svc_typed.handler()
async def run_typed_call_chaining(ctx: restate.Context, prompt: Prompt) -> str:
    """Chains multiple LLM calls sequentially, where each step processes the previous step's output."""

    agent = Agent(
        model="openai:gpt-4o",
        instructions="Be concise and follow instructions exactly.",
    )
    restate_agent = RestateAgent(agent, restate_context=ctx)

    async def agent_call(prompt_text: str) -> str:
        result = await restate_agent.run(prompt_text)
        return result.output

    result = await ctx.run_typed(
        "Extract metrics",
        agent_call,
        RunOptions(max_attempts=3),
        prompt_text=f"Extract only the numerical values and their associated metrics from the text. "
        f"Format each as 'metric name: metric' on a new line. Input: {prompt.message}",
    )

    result2 = await ctx.run_typed(
        "Sort metrics",
        agent_call,
        RunOptions(max_attempts=3),
        prompt_text=f"Sort all lines in descending order by numerical value. Input: {result}",
    )

    result3 = await ctx.run_typed(
        "Format as table",
        agent_call,
        RunOptions(max_attempts=3),
        prompt_text=f"Format the sorted data as a markdown table with columns 'Metric Name' and 'Value'. Input: {result2}",
    )

    return result3
