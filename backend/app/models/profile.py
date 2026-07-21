import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Text, Float, DateTime
from sqlalchemy.orm import mapped_column
from ..core.database import Base


class Profile(Base):
    __tablename__ = "profile"

    id = Column(Integer, primary_key=True, default=1)
    full_name = Column(String(200))
    email = Column(String(200))
    phone = Column(String(50))
    location = Column(String(200))
    linkedin_url = Column(String(500))
    website = Column(String(500))
    professional_summary = Column(Text)
    target_roles = Column(Text, default="[]")  # JSON array
    nz_work_rights = Column(String(100), default="Citizen/PR")
    setup_complete = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkExperience(Base):
    __tablename__ = "work_experience"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company = Column(String(200), nullable=False)
    role = Column(String(200), nullable=False)
    start_date = Column(String(20))
    end_date = Column(String(20))
    is_current = Column(Boolean, default=False)
    location = Column(String(200))
    description = Column(Text)
    key_responsibilities = Column(Text, default="[]")  # JSON array
    technologies = Column(Text, default="[]")  # JSON array
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    category = Column(String(50))  # technical, soft, tool, framework, process
    proficiency = Column(String(50))  # expert, proficient, familiar, learning
    years_experience = Column(Float)
    confidence = Column(String(20), default="confirmed")  # confirmed, inferred, weak, do_not_use
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Certification(Base):
    __tablename__ = "certifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(300), nullable=False)
    issuer = Column(String(200))
    date_obtained = Column(String(20))
    expiry_date = Column(String(20))
    credential_id = Column(String(200))
    url = Column(String(500))
    in_progress = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    situation = Column(Text)
    action = Column(Text)
    result = Column(Text)
    tools_involved = Column(Text, default="[]")   # JSON array
    skills_demonstrated = Column(Text, default="[]")  # JSON array
    who_benefited = Column(Text)
    measurable_outcome = Column(Text)
    confidence = Column(String(20), default="confirmed")
    bullet_plain = Column(Text)
    bullet_strong = Column(Text)
    bullet_senior = Column(Text)
    bullet_ats = Column(Text)
    source = Column(String(300))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    role = Column(String(200))
    technologies = Column(Text, default="[]")  # JSON array
    outcomes = Column(Text)
    url = Column(String(500))
    date_range = Column(String(100))
    confidence = Column(String(20), default="confirmed")
    created_at = Column(DateTime, default=datetime.utcnow)


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    tools_involved = Column(Text, default="[]")  # JSON array
    skills_demonstrated = Column(Text, default="[]")  # JSON array
    outcome = Column(Text)
    value = Column(Text)
    confidence = Column(String(20), default="confirmed")
    notes = Column(Text)
    source = Column(String(300))
    created_at = Column(DateTime, default=datetime.utcnow)


class StylePreferences(Base):
    __tablename__ = "style_preferences"

    id = Column(Integer, primary_key=True, default=1)
    bullet_style = Column(String(20), default="dash")
    tone = Column(String(50), default="professional")
    preferred_cv_length = Column(String(20), default="2-pages")
    avoid_phrases = Column(Text, default="[]")  # JSON array
    preferred_phrases = Column(Text, default="[]")  # JSON array
    example_bullets = Column(Text, default="[]")  # JSON array
    notes = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExampleCV(Base):
    __tablename__ = "example_cvs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(300), nullable=False)
    original_filename = Column(String(300))
    analysis_path = Column(String(500))
    structure_path = Column(String(500))
    sections = Column(Text, default="[]")  # JSON array
    section_order = Column(Text, default="[]")  # JSON array
    tone = Column(String(100))
    bullet_style = Column(String(100))
    formatting_notes = Column(Text)
    strengths = Column(Text, default="[]")  # JSON array
    weaknesses = Column(Text, default="[]")  # JSON array
    layout_ideas = Column(Text, default="[]")  # JSON array
    raw_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
