from Base import Base
from sqlalchemy import Column, Integer, String, Text

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

class Job(Base):
    __tablename__ = 'jobs'
	
    # Job Identifiers
    id          = Column(Integer, primary_key=True)
    job_id      = Column(String(32), unique=True)
    name        = Column(String(64))
    engine_id   = Column(Integer)
	
    # Job Details
    session     = Column(Text)
    target      = Column(Text)
    conditions  = Column(Text)
    requests    = Column(Text)
    agent       = Column(Text)

    # Job Status Information
    status      = Column(Integer)
    node        = Column(Text)
    c_m_index   = Column(Integer)
    t_m_index   = Column(Integer)
    crashes     = Column(Integer)
    warnings    = Column(Integer)
    job_loaded  = Column(Integer)
    job_started = Column(Integer)
    job_stopped = Column(Integer)

