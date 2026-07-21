from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from ..core.database import Base


class ScanSearch(Base):
    __tablename__ = "scan_searches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    keywords = Column(String(500))          # space-separated search terms
    sites = Column(Text)                    # JSON list of site keys
    created_at = Column(DateTime, default=datetime.utcnow)
    last_scanned = Column(DateTime)


class ScannedJob(Base):
    __tablename__ = "scanned_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_key = Column(String(500), unique=True)   # "source:external_id" — dedup key
    title = Column(String(500))
    company = Column(String(300))
    location = Column(String(300))
    url = Column(String(1000))
    description_snippet = Column(Text)
    date_posted = Column(String(100))
    source = Column(String(50))             # seek | absoluteit | hays | potentia | trademe
    status = Column(String(20), default="new")   # new | seen | dismissed
    search_keywords = Column(String(500))   # which search found this
    first_seen = Column(DateTime, default=datetime.utcnow)
