"""Pydantic schemas for evidence-grounded resume scoring."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    excerpt: str = Field(min_length=1, max_length=400)
    relevance: str = Field(min_length=1, max_length=400)
    resume_section: str | None = Field(default=None, max_length=80)


class CriterionAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_status: Literal["SUPPORTED", "PARTIAL", "NOT_FOUND", "UNCLEAR"]
    score: int | None = Field(default=None, ge=0, le=100)
    rationale: str = Field(min_length=1, max_length=900)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=12)
    missing_or_unclear: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_evidence_state(self):
        if self.evidence_status in {"SUPPORTED", "PARTIAL"}:
            if self.score is None:
                raise ValueError("Supported or partial evidence must have a numeric score.")
            if not self.evidence:
                raise ValueError("Supported or partial evidence must include at least one resume excerpt.")
        else:
            if self.score is not None:
                raise ValueError("NOT_FOUND and UNCLEAR evidence must not be assigned a numeric score.")
        return self


class ResumeScoringOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_skills: CriterionAssessment
    relevant_experience: CriterionAssessment
    role_related_projects: CriterionAssessment
    education_certifications: CriterionAssessment
    other_job_evidence: CriterionAssessment
    overall_assessment: str = Field(min_length=1, max_length=1800)
    additional_missing_or_unclear: list[str] = Field(default_factory=list, max_length=20)
    warnings: list[str] = Field(default_factory=list, max_length=20)
