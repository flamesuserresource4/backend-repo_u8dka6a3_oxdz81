"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, time, datetime


class DailyItem(BaseModel):
    """
    Daily planner item schema
    Collection name: "dailyitem"
    """
    title: str = Field(..., min_length=1, max_length=200, description="Task or event title")
    notes: Optional[str] = Field(None, max_length=2000, description="Optional notes")
    day: date = Field(..., description="Calendar date for this item (YYYY-MM-DD)")
    start_time: Optional[time] = Field(None, description="Start time (HH:MM)")
    end_time: Optional[time] = Field(None, description="End time (HH:MM)")
    notify_at: Optional[datetime] = Field(None, description="Exact timestamp to notify (UTC ISO)")
    completed: bool = Field(False, description="Completion status")
    priority: Optional[str] = Field(None, description="low | medium | high")
    tags: List[str] = Field(default_factory=list, description="Labels for grouping")
    notified: bool = Field(False, description="Whether a notification was already delivered")
