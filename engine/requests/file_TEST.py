# =============================================================================
# Basic TEST
# This file is part of the FuzzLabs Fuzzing Framework
# =============================================================================

import syslog
from sulley import *

s_initialize("TEST")
s_binary("0x00")
s_byte(0x00, full_range=True)
s_string("a")
s_string("a")
