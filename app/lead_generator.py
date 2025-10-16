from typing import List
import json
import os

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent
from restate import RunOptions
from tavily import AsyncTavilyClient
import logfire
import restate

from app.schemas.lead_generator import Company
from app.restate import RestateAgent
from app.schemas.lead_generator import LinkedInLeadQueries, TavilyResponse, TopLeads
from app.system_prompts.lead_generator import (
    structured_instructions,
    unstructured_instructions,
    generate_lead_scoring_instructions,
    generate_outreach_content_instructions,
)

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()


class QueryResults(BaseModel):
    query: str
    description: str
    results: TavilyResponse


class TierResults(BaseModel):
    name: str
    description: str
    priority: int
    results: List[QueryResults]


class Leads(BaseModel):
    company_context: str
    total_tiers: int
    usage_instructions: List[str]
    tiers: List[TierResults]


lead_generator_service = restate.Service("Lead_Generator_Service")


@lead_generator_service.handler()
async def run_lead_generator(ctx: restate.Context, company: Company) -> str:
    prompt = f"""
    "company_name": "{company.company_name}"
    "what_we_do": "{company.what_we_do}"
    "target_market": "{company.target_market}"
    """
    with logfire.span("Generating leads") as span:

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

        structured_restate_agent: RestateAgent[None, LinkedInLeadQueries] = (
            RestateAgent(structured_leads_agent, restate_context=ctx)
        )

        async def structured_leads_agent_call(prompt_text: str) -> LinkedInLeadQueries:
            result = await structured_restate_agent.run(prompt_text)
            return result.output

        with logfire.span("Generating Query Plan") as span:
            unstructured_output: str = await ctx.run_typed(
                "Freeform leads generator",
                unstructured_agent_call,
                RunOptions(max_attempts=3, type_hint=str),
                prompt_text=prompt,
            )
        with logfire.span("Generating Structured Query Config") as span:
            structured_output: LinkedInLeadQueries = await ctx.run_typed(
                "Structured leads generator",
                structured_leads_agent_call,
                RunOptions(max_attempts=3, type_hint=LinkedInLeadQueries),
                prompt_text=f"Structure these LinkedIn search queries for automated lead generation: {unstructured_output}",
            )

        async def query_executor_call(structured_output: LinkedInLeadQueries):
            tavily_client = AsyncTavilyClient(api_key=TAVILY_API_KEY)

            company_context = structured_output.company_context
            total_tiers = structured_output.total_tiers
            usage_instructions = structured_output.usage_instructions
            tiers = structured_output.priority_tiers

            tier_results = []
            for tier in tiers:
                with logfire.span(f"Tier {tier.priority_level} queries") as span:
                    name = tier.tier_name
                    description = tier.tier_description
                    priority = tier.priority_level
                    query_results = []
                    for q in tier.queries:
                        with logfire.span(f"{q.query}", query=q.query) as span:
                            query = f"{q.query} site:linkedin.com"
                            response = await tavily_client.search(
                                query=query,
                                include_raw_content=True,
                                max_results=10,
                                include_domains=["linkedin.com"],
                            )
                            query_results.append(
                                QueryResults(
                                    query=q.query,
                                    description=q.description,
                                    results=TavilyResponse(**response),
                                )
                            )
                    tier_results.append(
                        TierResults(
                            name=name,
                            description=description,
                            priority=priority,
                            results=query_results,
                        )
                    )
            return Leads(
                company_context=company_context,
                total_tiers=total_tiers,
                usage_instructions=usage_instructions,
                tiers=tier_results,
            )

        with logfire.span("Executing queries") as span:
            leads: Leads = await ctx.run_typed(
                "Executing queries",
                query_executor_call,
                RunOptions(max_attempts=3, type_hint=Leads),
                structured_output,
            )
        with logfire.span("Saving results") as span:
            with open("leads.json", "w", encoding="utf-8") as f:
                json.dump(leads.model_dump(), f, indent=2)

        top_leads = [
            {
                "title": lead.title,
                "url": lead.url,
                "content": lead.content,
                "score": lead.score,
            }
            for lead in sorted(
                (
                    result
                    for tier in leads.tiers
                    if tier.priority == 1
                    for query_results in tier.results
                    for result in query_results.results.results
                ),
                key=lambda x: x.score,
                reverse=True,
            )
        ]

        scoring_instructions = generate_lead_scoring_instructions(company)

        scoring_agent = Agent[None, TopLeads](
            "openai:gpt-4.1",
            instructions=scoring_instructions,
            output_type=TopLeads,
            retries=2,
        )
        scoring_restate_agent = RestateAgent[None, TopLeads](
            scoring_agent, restate_context=ctx
        )

        async def scoring_agent_call(prompt_text: str) -> TopLeads:
            result = await scoring_restate_agent.run(prompt_text)
            return result.output

        with logfire.span("Scoring top leads") as span:
            scored_leads: TopLeads = await ctx.run_typed(
                "Scoring top leads",
                scoring_agent_call,
                RunOptions(max_attempts=3, type_hint=TopLeads),
                prompt_text=json.dumps(top_leads, indent=2),
            )
        with logfire.span("Saving scored leads") as span:
            with open("scored_leads.json", "w", encoding="utf-8") as f:
                json.dump(scored_leads.model_dump(), f, indent=2)

        return scored_leads.model_dump()

        # async def lead_enrichment_call(leads: Leads, company: Company):
        #     with logfire.span("Company context") as span:
        #         logfire.info(company.company_name)
        #         logfire.info(company.what_we_do)
        #         logfire.info(company.target_market)
        #     return leads

        # with logfire.span("Enriching leads") as span:
        #     enriched_leads: Leads = await ctx.run_typed(
        #         "Enriching leads",
        #         lead_enrichment_call,
        #         RunOptions(max_attempts=3, type_hint=Leads),
        #         leads=leads,
        #         company=company,
        #     )

        # with logfire.span("Saving enriched leads") as span:
        #     with open("enriched_leads.json", "w", encoding="utf-8") as f:
        #         json.dump(enriched_leads.model_dump(), f, indent=2)

        # return enriched_leads.model_dump()
