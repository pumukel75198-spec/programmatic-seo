"""Strict data models (Pydantic v2) for the FlowMatrix content pipeline.

These models are the contract between the LLM and the validator. They are
intentionally strict for NEWLY generated content: missing snippets, too few
actions or an incomplete glossary are hard errors, not warnings.

The number of steps is *variable* (``MIN_STEPS``..``MAX_STEPS``) and follows
the real technical complexity of the topic – there is no fixed 5-step rule.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from . import config


class Link(BaseModel):
    model_config = ConfigDict(extra="allow")
    label: str
    url: str


class Command(BaseModel):
    model_config = ConfigDict(extra="allow")
    label: str
    language: str = "bash"
    code: str


class ConfigEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    key: str
    value: str
    description: str = ""


class Step(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str
    description: str
    code_snippet: str
    technical_explanation: str
    actions: list[str] = Field(min_length=3)
    commands: list[Command] = Field(default_factory=list)
    config: list[ConfigEntry] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(min_length=2)
    expectedResult: str
    links: list[Link] = Field(default_factory=list)


class GlossaryEntry(BaseModel):
    term: str
    definition: str


class TroubleshootingEntry(BaseModel):
    problem: str
    solution: str


class WorkflowDetails(BaseModel):
    model_config = ConfigDict(extra="allow")
    difficulty: str
    duration: str
    tools: list[str] = Field(default_factory=list)
    steps: list[Step] = Field(
        min_length=config.MIN_STEPS, max_length=config.MAX_STEPS
    )
    useCase: str = ""
    prerequisites: list[str] = Field(min_length=config.PREREQUISITES_MIN)
    glossary: list[GlossaryEntry] = Field(min_length=config.GLOSSARY_TERMS_MIN)
    troubleshooting: list[TroubleshootingEntry] = Field(
        min_length=config.TROUBLESHOOTING_MIN
    )
    resources: list[Link] = Field(default_factory=list)


class Workflow(BaseModel):
    model_config = ConfigDict(extra="allow")
    slug: str
    title: str
    description: str
    category: str
    tags: list[str] = Field(default_factory=list)
    created_and_verified_at: str = ""
    details: WorkflowDetails


class API(BaseModel):
    """Loose model for the existing API catalogue (extra keys are kept)."""

    model_config = ConfigDict(extra="allow")
    slug: str
    title: str
    description: str
    category: str
    tags: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class AlternativeItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    description: str


class Alternative(BaseModel):
    model_config = ConfigDict(extra="allow")
    slug: str
    title: str
    description: str
    category: str
    tags: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class GenerationResult(BaseModel):
    """Outcome of a single self-healing generation attempt."""

    model_config = ConfigDict(extra="allow")
    ok: bool
    data: dict[str, Any] | None = None
    errors: list[str] = Field(default_factory=list)
    attempts: int = 0
