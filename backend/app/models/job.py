from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from ..core.database import Base


class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_folder = Column(String(500), nullable=False)
    company = Column(String(200))
    role = Column(String(200))
    recruiter_name = Column(String(200))
    location = Column(String(200))
    work_type = Column(String(50))  # remote, hybrid, on-site
    salary_range = Column(String(100))
    job_description_raw = Column(Text)
    job_analysis = Column(Text)       # JSON
    match_scorecard = Column(Text)    # JSON — the original LLM-only fit assessment, unchanged
    job_requirements = Column(Text)   # JSON — structured JD Intelligence (see services/matching)
    job_match_result = Column(Text)   # JSON — explainable Job Match score + coverage/recommendations
    cover_letter = Column(Text)
    cv_adjustment_notes = Column(Text)
    tailored_cv = Column(Text)
    custom_cv = Column(Text)                  # markdown — generated from selected Job Match fixes only
    custom_cv_fixes_applied = Column(Text)    # JSON — requirement names of the fixes actually applied
    interview_prep = Column(Text)
    linkedin_angle = Column(Text)
    recruiter_message = Column(Text)
    company_research = Column(Text)
    session_notes = Column(Text)
    status = Column(String(50), default="draft")  # draft, applied, interviewing, offered, rejected, withdrawn
    applied_date = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
