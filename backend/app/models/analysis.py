from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from ..core.database import Base


class AnalysisSnapshot(Base):
    """One point-in-time Job Match result for an application, kept so the
    history dashboard (and, later, before/after re-scan) can show how the
    score changed over time rather than only ever seeing the latest run."""
    __tablename__ = "analysis_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False)
    cv_version_id = Column(Integer, ForeignKey("cv_versions.id"), nullable=True)
    job_match_score = Column(Integer)
    label = Column(String(50))  # "master_cv" | "tailored_cv" | "custom_cv" — what was scored
    summary_json = Column(Text)  # the full job_match_result at the time of this snapshot
    created_at = Column(DateTime, default=datetime.utcnow)
