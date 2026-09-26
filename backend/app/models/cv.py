from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from ..core.database import Base


class CVVersion(Base):
    __tablename__ = "cv_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_name = Column(String(200))
    content_markdown = Column(Text)
    content_json = Column(Text)
    # JSON — cached Recruiter Readiness result (brutal_review + computed score).
    # This CV version is immutable once created, so the result never goes
    # stale; a new CV always gets a new row and needs a fresh computation.
    recruiter_readiness_result = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AppSettings(Base):
    __tablename__ = "app_settings"

    key = Column(String(200), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
