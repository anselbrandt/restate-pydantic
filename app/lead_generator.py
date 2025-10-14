from pydantic import BaseModel
from pydantic_ai import Agent
from restate import RunOptions
import restate

from app.data.example_prompt import example_prompt
from app.restate import RestateAgent
from app.schemas.lead_generator import LinkedInLeadQueries
from app.system_prompts.lead_generator import (
    structured_instructions,
    unstructured_instructions,
)

lead_generator_service = restate.Service("Lead_Generator_Service")


class Prompt(BaseModel):
    prompt: str = example_prompt


@lead_generator_service.handler()
async def run_lead_generator(ctx: restate.Context, prompt: Prompt) -> str:

    unstructured_leads_agent = Agent(
        "openai:gpt-4.1",
        instructions=unstructured_instructions,
        retries=2,
    )
    unstructured_restate_agent = RestateAgent(
        unstructured_leads_agent, restate_context=ctx
    )

    async def unstructured_agent_call(prompt_text: str) -> str:
        result = await unstructured_restate_agent.run(prompt_text)
        return result.output

    structured_leads_agent = Agent[None, LinkedInLeadQueries](
        "openai:gpt-4.1-mini",
        instructions=structured_instructions,
        output_type=LinkedInLeadQueries,
        retries=3,
    )

    structured_restate_agent: RestateAgent[None, LinkedInLeadQueries] = RestateAgent(
        structured_leads_agent, restate_context=ctx
    )

    async def structured_leads_agent_call(prompt_text: str) -> LinkedInLeadQueries:
        result = await structured_restate_agent.run(prompt_text)
        return result.output

    unstructured_output = await ctx.run_typed(
        "Freeform leads generator",
        unstructured_agent_call,
        RunOptions(max_attempts=3),
        prompt_text=prompt.prompt,
    )

    structured_result = await ctx.run_typed(
        "Structured leads generator",
        structured_leads_agent_call,
        RunOptions(max_attempts=3, type_hint=LinkedInLeadQueries),
        prompt_text=f"Structure these LinkedIn search queries for automated lead generation: {unstructured_output}",
    )

    return structured_result.model_dump_json()
