# =============================================================================
# Basic TEST
# This file is part of the FuzzLabs Fuzzing Framework
# =============================================================================

import syslog
from sulley import *

s_initialize("TEST")
if s_block_start("TEST_BLOCK"):
    s_static("BEGIN")
    s_size("TEST_BLOCK")
    s_delim(",", fuzzable=True, name="DELIM_TEST_3")
    s_group("GROUP_TEST_1", values=["TEST-1", "TEST-2"])
    s_random("RANDOM_TEST_1", min_length=1, max_length=4, num_mutations=20, fuzzable=True, step=2, name="RANDOM_TEST_1")
    s_static("STATIC_TEST", name="STATIC_TEST_1")
    s_binary([0x41, 0x42, 0x43], fuzzable=False, name="BINARY_TEST_1")
    s_binary([0x41, 0x42, 0x43], fuzzable=True, name="BINARY_TEST_2")
    s_byte(0x00, format="binary", synchsafe=True, signed=True, full_range=True, fuzzable=True, name="BYTE_TEST_1")
    s_word(0x00, format="binary", synchsafe=False, signed=True, full_range=False, fuzzable=True, name="WORD_TEST_1")
    s_dword(0x00, format="binary", synchsafe=True, signed=True, full_range=False, fuzzable=True, name="DWORD_TEST_1")
    s_qword(0x00, format="binary", synchsafe=True, signed=True, full_range=False, fuzzable=True, name="QWORD_TEST_1")
    # HAVING A SMALL SIZE (e.g. 10) FOR S_STRING BELOW RESULTS IN INCOMPLETE STATUS AND 
    # JOB SHOWS UP AS NEVER FINISHING.
    s_string("STRING_TEST_1", size=50, padding="\xFE", encoding="ascii", compression="zlib", fuzzable=True, max_len=20, name="STRING_TEST_1")
    s_string("END")
s_block_end("TEST_BLOCK")
s_repeat("TEST_BLOCK", min_reps=0, max_reps=10, step=2, fuzzable=True, name="REPEAT_TEST_1")
s_checksum("TEST_BLOCK", algorithm="crc32", length=4, endian=">")
s_padding("TEST_BLOCK", byte_align=4, pad_byte=0x01, max_reps=16, step=2, fuzzable=True, name="PADDING_TEST_1")
s_static("\r\n\r\n")
