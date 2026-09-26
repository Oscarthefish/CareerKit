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
    employer_public_name = Column(String(200))  # optional redacted/generic name for public-facing output
    role = Column(String(200), nullable=False)
    alternative_titles = Column(Text, default="[]")  # JSON array
    start_date = Column(String(20))
    end_date = Column(String(20))
    is_current = Column(Boolean, default=False)
    location = Column(String(200))
    description = Column(Text)
    key_responsibilities = Column(Text, default="[]")  # JSON array
    technologies = Column(Text, default="[]")  # JSON array
    order_index = Column(Integer, default=0)
    # public, cv_safe, recruiter_only, interview_only, confidential, do_not_use
    confidentiality_level = Column(String(20), default="cv_safe")
    created_at = Column(DateTime, default=datetime.utcnow)


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    aliases = Column(Text, default="[]")  # JSON array — legacy/rebranded names, e.g. Cisco AMP -> Secure Endpoint
    category = Column(String(50))  # technical, soft, tool, framework, process
    # For category="tool" only: the tool-type heading it's grouped under on the CV
    # (e.g. "SIEM", "EDR", "Firewalls", "Email Security"). Lets the CV's Platforms
    # & Tools section be built deterministically instead of trusting the model to
    # group and deduplicate product names correctly every time.
    tool_category = Column(String(50))
    # Real and confirmed, but not every real tool needs to take up space on the
    # CV — commodity tools a recruiter would expect and that are better raised
    # in an interview can be tracked here without cluttering Platforms & Tools.
    # Still included in the full skills data used for scorecards, LinkedIn, etc.
    include_on_cv = Column(Boolean, default=True)
    proficiency = Column(String(50))  # expert, proficient, familiar, learning
    years_experience = Column(Float)
    last_used = Column(String(20))
    production_experience = Column(Boolean, default=True)  # hands-on/production vs training-only exposure
    # confirmed_hands_on, working_knowledge, training_exposure, familiarity,
    # interest, unverified, do_not_include (legacy: confirmed, inferred, weak, do_not_use)
    confidence = Column(String(30), default="confirmed_hands_on")
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
    # active, expired, retired_legacy, unverified_status — for wording like "earned 2018" vs "currently active"
    status = Column(String(30), default="active")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Training(Base):
    """Professional training and courses that are NOT certifications.

    Kept separate from Certification so training exposure can never be
    silently presented as a passed certification exam.
    """
    __tablename__ = "training"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    provider = Column(String(200))
    date = Column(String(20))
    delivery_type = Column(String(50))  # classroom, online, self-paced, conference-workshop
    duration = Column(String(50))
    # completed, enrolled, in_progress, purchased_not_started, unconfirmed
    completion_status = Column(String(30), default="completed")
    related_certification = Column(String(200))
    tools = Column(Text, default="[]")  # JSON array
    skills = Column(Text, default="[]")  # JSON array
    evidence = Column(Text)
    include_by_default = Column(Boolean, default=True)
    confidence = Column(String(30), default="confirmed_hands_on")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class CommunityInvolvement(Base):
    __tablename__ = "community_involvement"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event = Column(String(300), nullable=False)
    location = Column(String(200))
    date = Column(String(50))
    # attendee, participant, speaker, organiser, regular_attendee
    participation_type = Column(String(50), default="attendee")
    notes = Column(Text)
    evidence = Column(Text)
    include_on_cv = Column(Boolean, default=False)
    include_on_linkedin = Column(Boolean, default=True)
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
    confidence = Column(String(30), default="confirmed_hands_on")
    confidentiality_level = Column(String(20), default="cv_safe")
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
    confidence = Column(String(30), default="confirmed_hands_on")
    confidentiality_level = Column(String(20), default="cv_safe")
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
    confidence = Column(String(30), default="confirmed_hands_on")
    confidentiality_level = Column(String(20), default="cv_safe")
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
