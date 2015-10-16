from Base import Base
from sqlalchemy import Column, Integer, String, Text

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

class Session(Base):
    __tablename__ = 'sessions'

    job_id              = Column(String(32), primary_key=True)
    proto               = Column(String(32))
    skip                = Column(Integer)
    sleep_time          = Column(Integer)
    restart_interval    = Column(Integer)
    timeout             = Column(Integer)
    crashes             = Column(Integer)
    warnings            = Column(Integer)
    total_num_mutations = Column(Integer)
    total_mutant_index  = Column(Integer)
    pause_flag          = Column(Integer)

