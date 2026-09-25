from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from ..core.database import Base


class CVVersion(Base):
    __tablename__ = "cv_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_name = Column(String(200))
    content_markdown = Column(Text)
    content_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class AppSettings(Base):
    __tablename__ = "app_settings"

    key = Column(String(200), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
