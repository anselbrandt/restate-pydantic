from typing import List, Optional, Dict, Any


from pydantic import BaseModel, Field

from app.data.example_prompt import (
    company_name,
    what_we_do,
    target_market,
)


class SearchQuery(BaseModel):
    query: str = Field(
        description="The search query string with only keywords, no quotes or special characters"
    )
    description: str = Field(description="Brief description of what this query targets")


class PriorityTier(BaseModel):
    tier_name: str = Field(description="Name of the priority tier")
    tier_description: str = Field(
        description="Description of why this tier is prioritized this way"
    )
    priority_level: int = Field(description="Priority level (1 = highest priority)")
    queries: List[SearchQuery] = Field(
        description="List of search queries for this tier"
    )


class LinkedInLeadQueries(BaseModel):
    company_context: str = Field(
        description="Brief context about the company these queries are for"
    )
    total_tiers: int = Field(description="Total number of priority tiers")
    priority_tiers: List[PriorityTier] = Field(
        description="Ordered list of priority tiers with their queries"
    )
    usage_instructions: List[str] = Field(
        description="Key instructions for using these queries effectively"
    )


class TavilyResult(BaseModel):
    url: str = Field(description="URL of the search result")
    title: str = Field(description="Title of the search result")
    content: str = Field(description="Content snippet from the search result")
    score: float = Field(description="Relevance score of the result")
    raw_content: Optional[str] = Field(
        default=None, description="Raw content if available"
    )


class TavilyResponse(BaseModel):
    query: str = Field(description="The search query that was executed")
    results: List[TavilyResult] = Field(description="List of search results")
    response_time: float = Field(description="Time taken to execute the search")
    request_id: str = Field(description="Unique identifier for this search request")


class SearchResults(BaseModel):
    search_results: List[Dict[str, Any]]
    priority_1_results: List[Dict[str, Any]]
    total_queries: int
    total_results: int
    company_context: str


class ScoredLead(BaseModel):
    url: str = Field(description="LinkedIn profile URL")
    title: str = Field(description="Profile title from search result")
    content: str = Field(description="Content snippet describing the profile")
    original_score: float = Field(description="Original Tavily relevance score")
    lead_score: float = Field(description="AI-calculated lead quality score (0-100)")
    reasoning: str = Field(description="Brief explanation for the lead score")
    decision_maker_level: str = Field(
        description="Estimated decision-making level: Executive/Senior/Mid/Junior"
    )
    company_relevance: str = Field(
        description="How relevant this lead is to the target company: High/Medium/Low"
    )
    outreach_priority: int = Field(
        description="Priority ranking for outreach (1-10, 1 being highest)"
    )


class ScoredLeadWithMessage(BaseModel):
    url: str = Field(description="LinkedIn profile URL")
    title: str = Field(description="Profile title from search result")
    content: str = Field(description="Content snippet describing the profile")
    original_score: float = Field(description="Original Tavily relevance score")
    lead_score: float = Field(description="AI-calculated lead quality score (0-100)")
    reasoning: str = Field(description="Brief explanation for the lead score")
    decision_maker_level: str = Field(
        description="Estimated decision-making level: Executive/Senior/Mid/Junior"
    )
    company_relevance: str = Field(
        description="How relevant this lead is to the target company: High/Medium/Low"
    )
    outreach_priority: int = Field(
        description="Priority ranking for outreach (1-10, 1 being highest)"
    )
    outreach_message: str = Field(
        description="Personalized 2-3 sentence outreach message for this lead"
    )


class TopLeads(BaseModel):
    company_context: str = Field(description="Context about the company seeking leads")
    total_leads_analyzed: int = Field(description="Total number of leads analyzed")
    top_leads: List[ScoredLead] = Field(
        description="Top 10 highest scoring leads for outreach"
    )
    selection_criteria: List[str] = Field(
        description="Key criteria used for lead selection"
    )
    outreach_recommendations: List[str] = Field(
        description="Strategic recommendations for outreach approach"
    )


class TopLeadsWithMessaging(BaseModel):
    company_context: str = Field(description="Context about the company seeking leads")
    total_leads_analyzed: int = Field(description="Total number of leads analyzed")
    top_leads: List[ScoredLeadWithMessage] = Field(
        description="Top 10 highest scoring leads with personalized outreach messages"
    )
    selection_criteria: List[str] = Field(
        description="Key criteria used for lead selection"
    )
    outreach_recommendations: List[str] = Field(
        description="Strategic recommendations for outreach approach"
    )


class Company(BaseModel):
    company_name: str = company_name
    what_we_do: str = what_we_do
    target_market: str = target_market
