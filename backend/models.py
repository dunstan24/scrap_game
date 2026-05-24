"""
Pydantic models for FastAPI request/response
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional


class ScrapeRequest(BaseModel):
    start_url: str = Field(
        default="https://www.pcgamingwiki.com/wiki/Category:Games",
        description="Starting URL for PCGamingWiki category list"
    )
    pages: int = Field(default=3, ge=1, description="Max pages to scrape")
    platform: Literal["pcgamingwiki"] = Field(
        default="pcgamingwiki",
        description="Scraping platform"
    )
    scrape_mode: Literal["all", "alphabet"] = Field(default="all", description="Mode of scraping")
    target_alphabet: Optional[str] = Field(default=None, description="Alphabet to scrape if mode is alphabet")
    skip_existing: bool = Field(default=True, description="Skip already scraped games")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "start_url": "https://www.pcgamingwiki.com/wiki/Category:Games",
                "pages": 3,
                "platform": "pcgamingwiki"
            }]
        }
    }


class JobStatus(BaseModel):
    job_id: int
    platform: str
    status: Literal["queued", "running", "paused", "cancelled", "done", "error"]
    progress: int = 0
    total_found: int = 0
    logs: list[str] = []
    error: Optional[str] = None
    output_file: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class ScrapeResponse(BaseModel):
    job_id: int
    message: str = "Scraping started"
    platform: str
