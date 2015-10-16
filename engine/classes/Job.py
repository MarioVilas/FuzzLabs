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
	
    # Job Details
    session     = Column(Text)
    target      = Column(Text)
    conditions  = Column(Text)
    requests    = Column(Text)
    agent       = Column(Text)
	
    # Job Status Information
    node        = Column(String(64))
    status      = Column(Integer)
    c_m_index   = Column(Integer)
    t_m_index   = Column(Integer)
    crashes     = Column(Integer)
    warnings    = Column(Integer)
    job_loaded  = Column(Integer)
    job_started = Column(Integer)
    job_stopped = Column(Integer)

