import restate
from pydantic_ai import Agent
from pydantic import BaseModel

from app.restate import RestateAgent


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

    # Create a Pydantic AI agent and wrap it with RestateAgent for automatic durability
    agent = Agent(model="openai:gpt-4o", instructions="Be concise and follow instructions exactly.")
    restate_agent = RestateAgent(agent, restate_context=ctx)

    # Step 1: Process the initial input with the first prompt
    result = await restate_agent.run(
        f"Extract only the numerical values and their associated metrics from the text. "
        f"Format each as 'metric name: metric' on a new line. Input: {prompt.message}"
    )

    # Step 2: Process the result from Step 1
    result2 = await restate_agent.run(
        f"Sort all lines in descending order by numerical value. Input: {result.output}"
    )

    # Step 3: Process the result from Step 2
    result3 = await restate_agent.run(
        f"Format the sorted data as a markdown table with columns 'Metric Name' and 'Value'. Input: {result2.output}"
    )

    return result3.output
