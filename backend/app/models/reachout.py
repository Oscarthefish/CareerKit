from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from ..core.database import Base


class ReachOut(Base):
    """A speculative outreach: a company you want to introduce yourself to
    even though they are not actively advertising a role.

    Unlike JobApplication (built around a specific job description), a
    ReachOut is built around company research: what the business does, its
    culture, and an angle for why you would be worth keeping in mind.
    """
    __tablename__ = "reach_outs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_folder = Column(String(500))
    company_name = Column(String(200), nullable=False)
    website_url = Column(String(500))
    linkedin_url = Column(String(500))
    industry = Column(String(200))
    location = Column(String(200))
    company_size = Column(String(100))

    # Research (filled in from real web research - Ollama has no internet access,
    # so this is expected to come from the user or an assistant with browsing, not generated locally)
    research_summary = Column(Text)      # what the business does, market position
    culture_notes = Column(Text)         # values, working style, public culture signals
    tech_security_notes = Column(Text)   # known stack, vendors, security posture signals
    recent_news = Column(Text)           # funding, incidents, expansion, leadership changes
    angle = Column(Text)                 # why reach out now, the pitch angle

    contact_name = Column(String(200))
    contact_role = Column(String(200))
    contact_email = Column(String(200))

    # identified -> researched -> letter_drafted -> sent -> follow_up_due -> responded -> archived
    status = Column(String(30), default="identified")
    date_identified = Column(String(20))
    date_sent = Column(String(20))
    follow_up_date = Column(String(20))

    intro_letter = Column(Text)
    cv_notes = Column(Text)
    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
