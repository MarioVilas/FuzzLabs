import random
import struct
import blocks
import zlib
import copy
import sex

# =============================================================================
#
# =============================================================================

class base_primitive (object):
    '''
    The primitive base class implements common functionality shared across most primitives.
    '''

    def __init__ (self):
        self.fuzz_complete  = False     # this flag is raised when the mutations are exhausted.
        self.fuzz_library   = []        # library of static fuzz heuristics to cycle through.
        self.fuzzable       = True      # flag controlling whether or not the given primitive is to be fuzzed.
        self.mutant_index   = 0         # current mutation index into the fuzz library.
        self.original_value = None      # original value of primitive.
        self.rendered       = ""        # rendered value of primitive.
        self.value          = None      # current value of primitive.

    def exhaust (self):
        '''
        Exhaust the possible mutations for this primitive.

        @rtype:  Integer
        @return: The number of mutations to reach exhaustion
        '''

        num = self.num_mutations() - self.mutant_index

        self.fuzz_complete  = True
        self.mutant_index   = self.num_mutations()
        self.value          = self.original_value

        return num

    def mutate (self):
        '''
        Mutate the primitive by stepping through the fuzz library, return False on completion.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        '''

        # if we've ran out of mutations, raise the completion flag.
        if self.mutant_index == self.num_mutations():
            self.fuzz_complete = True

        # if fuzzing was disabled or complete, and mutate() is called, ensure the original value is restored.
        if not self.fuzzable or self.fuzz_complete:
            self.value = self.original_value
            return False

        # update the current value from the fuzz library.
        self.value = self.fuzz_library[self.mutant_index]

        # increment the mutation count.
        self.mutant_index += 1

        return True

    def num_mutations (self):
        '''
        Calculate and return the total number of mutations for this individual primitive.

        @rtype:  Integer
        @return: Number of mutated forms this primitive can take
        '''

        return len(self.fuzz_library)

    def render (self):
        '''
        Nothing fancy on render, simply return the value.
        '''

        self.rendered = self.value
        return self.rendered

    def reset (self):
        '''
        Reset this primitive to the starting mutation state.
        '''

        self.fuzz_complete  = False
        self.mutant_index   = 0
        self.value          = self.original_value

# =============================================================================
#
# =============================================================================

class delim (base_primitive):
    def __init__ (self, value, fuzzable=True, name=None):
        '''
        Represent a delimiter such as :,\r,\n, ,=,>,< etc... Mutations include repetition, substitution and exclusion.

        @type  value:    Character
        @param value:    Original value
        @type  fuzzable: Boolean
        @param fuzzable: (Optional, def=True) Enable/disable fuzzing of this primitive
        @type  name:     String
        @param name:     (Optional, def=None) Specifying a name gives you direct access to a primitive
        '''

        self.value         = self.original_value = value
        self.fuzzable      = fuzzable
        self.name          = name

        self.s_type        = "delim"   # for ease of object identification
        self.rendered      = ""        # rendered value
        self.fuzz_complete = False     # flag if this primitive has been completely fuzzed
        self.fuzz_library  = []        # library of fuzz heuristics
        self.mutant_index  = 0         # current mutation number

        if not value:
            raise sex.SullyRuntimeError("'%s' primitive requires a value" % self.s_type)
        if not type(value) is str:
            raise sex.SullyRuntimeError("'%s' primitive value has to be of type str" % self.s_type)
        if fuzzable != True and fuzzable != False:
            raise sex.SullyRuntimeError("'%s' primitive has invalid value for parameter 'fuzzable'" % self.s_type)

        #
        # build the library of fuzz heuristics.
        #

        # if the default delim is not blank, repeat it a bunch of times.
        if self.value:
            self.fuzz_library.append(self.value * 2)
            self.fuzz_library.append(self.value * 5)
            self.fuzz_library.append(self.value * 10)
            self.fuzz_library.append(self.value * 25)
            self.fuzz_library.append(self.value * 100)
            self.fuzz_library.append(self.value * 500)
            self.fuzz_library.append(self.value * 1000)

        # try ommitting the delimiter.
        self.fuzz_library.append("")

        # if the delimiter is a space, try throwing out some tabs.
        if self.value == " ":
            self.fuzz_library.append("\t")
            self.fuzz_library.append("\t" * 2)
            self.fuzz_library.append("\t" * 100)

        # toss in some other common delimiters:
        self.fuzz_library.append(" ")
        self.fuzz_library.append("\t")
        self.fuzz_library.append("\t " * 100)
        self.fuzz_library.append("\t\r\n" * 100)
        self.fuzz_library.append("!")
        self.fuzz_library.append("@")
        self.fuzz_library.append("#")
        self.fuzz_library.append("$")
        self.fuzz_library.append("%")
        self.fuzz_library.append("^")
        self.fuzz_library.append("&")
        self.fuzz_library.append("*")
        self.fuzz_library.append("(")
        self.fuzz_library.append(")")
        self.fuzz_library.append("-")
        self.fuzz_library.append("_")
        self.fuzz_library.append("+")
        self.fuzz_library.append("=")
        self.fuzz_library.append(":")
        self.fuzz_library.append(": " * 100)
        self.fuzz_library.append(":7" * 100)
        self.fuzz_library.append(";")
        self.fuzz_library.append("'")
        self.fuzz_library.append("\"")
        self.fuzz_library.append("/")
        self.fuzz_library.append("\\")
        self.fuzz_library.append("?")
        self.fuzz_library.append("<")
        self.fuzz_library.append(">")
        self.fuzz_library.append(".")
        self.fuzz_library.append(",")
        self.fuzz_library.append("\r")
        self.fuzz_library.append("\n")
        self.fuzz_library.append("\r\n" * 64)
        self.fuzz_library.append("\r\n" * 128)
        self.fuzz_library.append("\r\n" * 512)

# =============================================================================
#
# =============================================================================

class group (base_primitive):
    def __init__ (self, name, values):
        '''
        This primitive represents a list of static values, stepping through each one on mutation. You can tie a block
        to a group primitive to specify that the block should cycle through all possible mutations for *each* value
        within the group. The group primitive is useful for example for representing a list of valid opcodes.

        @type  name:   String
        @param name:   Name of group
        @type  values: List or raw data
        @param values: List of possible raw values this group can take.
        '''

        self.name           = name
        self.values         = values
        self.fuzzable       = True

        self.s_type         = "group"

        if not name:
            raise sex.SullyRuntimeError("'%s' primitive requires a name" % self.s_type)
        if not type(name) is str:
            raise sex.SullyRuntimeError("'%s' primitive name has to be of type str" % self.s_type)
        if not type(values) is list:
            raise sex.SullyRuntimeError("'%s' primitive requires values to be of type list" % self.s_type)

        self.value          = self.values[0]
        self.original_value = self.values[0]
        self.rendered       = ""
        self.fuzz_complete  = False
        self.mutant_index   = 0

        # sanity check that values list only contains strings (or raw data)
        if self.values != []:
            for val in self.values:
                assert type(val) is str, "Value list may only contain strings or raw data"


    def mutate (self):
        '''
        Move to the next item in the values list.

        @rtype:  False
        @return: False
        '''

        if self.mutant_index == self.num_mutations():
            self.fuzz_complete = True

        # if fuzzing was disabled or complete, and mutate() is called, ensure the original value is restored.
        if not self.fuzzable or self.fuzz_complete:
            self.value = self.values[0]
            return False

        # step through the value list.
        self.value = self.values[self.mutant_index]

        # increment the mutation count.
        self.mutant_index += 1

        return True


    def num_mutations (self):
        '''
        Number of values in this primitive.

        @rtype:  Integer
        @return: Number of values in this primitive.
        '''

        return len(self.values)

# =============================================================================
#
# =============================================================================

class random_data (base_primitive):
    def __init__ (self, value, min_length, max_length, max_mutations=25, fuzzable=True, step=None, name=None):
        '''
        Generate a random chunk of data while maintaining a copy of the original. A random length range can be specified.
        For a static length, set min/max length to be the same.

        @type  value:         Raw
        @param value:         Original value
        @type  min_length:    Integer
        @param min_length:    Minimum length of random block
        @type  max_length:    Integer
        @param max_length:    Maximum length of random block
        @type  max_mutations: Integer
        @param max_mutations: (Optional, def=25) Number of mutations to make before reverting to default
        @type  fuzzable:      Boolean
        @param fuzzable:      (Optional, def=True) Enable/disable fuzzing of this primitive
        @type  step:          Integer
        @param step:          (Optional, def=None) If not null, step count between min and max reps, otherwise random
        @type  name:          String
        @param name:          (Optional, def=None) Specifying a name gives you direct access to a primitive
        '''

        self.value         = self.original_value = str(value)
        self.min_length    = min_length
        self.max_length    = max_length
        self.max_mutations = max_mutations
        self.fuzzable      = fuzzable
        self.step          = step
        self.name          = name

        self.s_type        = "random_data"  # for ease of object identification

        if not value:
            raise sex.SullyRuntimeError("'%s' primitive requires a default value" % self.s_type)
        if name and not type(name) is str:
            raise sex.SullyRuntimeError("'%s' primitive name has to be of type str" % self.s_type)
        if min_length and not type(min_length) is int:
            raise sex.SullyRuntimeError("'%s' primitive requires min_length to be of type int" % self.s_type)
        if max_length and not type(max_length) is int:
            raise sex.SullyRuntimeError("'%s' primitive requires max_length to be of type int" % self.s_type)
        if max_mutations and not type(max_mutations) is int:
            raise sex.SullyRuntimeError("'%s' primitive requires max_mutations to be of type int" % self.s_type)
        if step and not type(step) is int:
            raise sex.SullyRuntimeError("'%s' primitive requires max_mutations to be of type int" % self.s_type)
        if fuzzable != True and fuzzable != False:
            raise sex.SullyRuntimeError("'%s' primitive requires fuzzable to be of type boolean" % self.s_type)

        self.rendered      = ""             # rendered value
        self.fuzz_complete = False          # flag if this primitive has been completely fuzzed
        self.mutant_index  = 0              # current mutation number

        if self.step:
            self.max_mutations = (self.max_length - self.min_length) / self.step + 1


    def mutate (self):
        '''
        Mutate the primitive value returning False on completion.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        '''

        # if we've ran out of mutations, raise the completion flag.
        if self.mutant_index == self.num_mutations():
            self.fuzz_complete = True

        # if fuzzing was disabled or complete, and mutate() is called, ensure the original value is restored.
        if not self.fuzzable or self.fuzz_complete:
            self.value = self.original_value
            return False

        # select a random length for this string.
        if not self.step:
            length = random.randint(self.min_length, self.max_length)
        # select a length function of the mutant index and the step.
        else:
            length = self.min_length + self.mutant_index * self.step

        # reset the value and generate a random string of the determined length.
        self.value = ""
        for i in xrange(length):
            self.value += chr(random.randint(0, 255))

        # increment the mutation count.
        self.mutant_index += 1

        return True


    def num_mutations (self):
        '''
        Calculate and return the total number of mutations for this individual primitive.

        @rtype:  Integer
        @return: Number of mutated forms this primitive can take
        '''

        return self.max_mutations


# =============================================================================
#
# =============================================================================

class static (base_primitive):
    def __init__ (self, value, name=None):
        '''
        Primitive that contains static content.

        @type  value: Raw
        @param value: Raw static data
        @type  name:  String
        @param name:  (Optional, def=None) Specifying a name gives you direct access to a primitive
        '''

        self.value         = self.original_value = value
        self.name          = name
        self.fuzzable      = False       # every primitive needs this attribute.
        self.mutant_index  = 0
        self.s_type        = "static"    # for ease of object identification
        self.rendered      = ""
        self.fuzz_complete = True

        if not value:
            raise sex.SullyRuntimeError("'%s' primitive requires a default value" % self.s_type)
        if name and not type(name) is str:
            raise sex.SullyRuntimeError("'%s' primitive name has to be of type str" % self.s_type)
        if value and not type(value) is str:
            raise sex.SullyRuntimeError("'%s' primitive value has to be of type str" % self.s_type)

    def mutate (self):
        '''
        Do nothing.

        @rtype:  False
        @return: False
        '''

        return False


    def num_mutations (self):
        '''
        Return 0.

        @rtype:  0
        @return: 0
        '''

        return 0

# =============================================================================
#
# =============================================================================

class binary (base_primitive):
    def __init__ (self, value, fuzzable, name=None):
        self.name           = name
        self.fuzzable       = fuzzable    # every primitive needs this attribute.
        self.mutant_index   = 0
        self.s_type         = "binary"    # for ease of object identification
        self.fuzz_complete  = False
        self.current_pos    = 0
        self.current_val    = 0
        self.original_value = copy.deepcopy(value)
        self.value          = []

        if not value:
            raise sex.SullyRuntimeError("'%s' primitive requires a default value" % self.s_type)
        if name and not type(name) is str:
            raise sex.SullyRuntimeError("'%s' primitive name has to be of type str" % self.s_type)

        if type(value) is list:
            self.value      = copy.deepcopy(value)
        elif type(value) is str:
            for byte_val in value:
                self.value.append(struct.unpack("B", byte_val)[0])
        else:
            raise sex.SullyRuntimeError("'%s' primitive value has to be of type list or str" % self.s_type)

        self.rendered       = ""

        self.max_int        = 0
        self.payloads       = [0x00, 0x01, 0xFF, 0x7F]
        self.position       = 0
        self.i_position     = 0
        self.edge_case_cnt  = 0
        self.int_sizes      = sorted(self.get_fuzz_sizes([1,2,3,4,8]))
        self.edge_cases     = self.gen_edge_cases()

    def byte_replace(self):
        self.value = copy.deepcopy(self.original_value)
        if self.current_val > 3:
            self.current_val = 0
            self.current_pos += 1

        if self.mutant_index >= (len(self.original_value) * 4):
            self.value = copy.deepcopy(self.original_value)
            return False

        self.value[self.current_pos] = self.payloads[self.current_val]
        self.current_val += 1
        self.mutant_index += 1

        return True

    def get_fuzz_sizes(self, int_sizes):
        sizes = []
        for int_size in int_sizes:
            if len(self.original_value) >= int_size:
                sizes.append(int_size)
        return sizes

    def gen_edge_cases(self):
        edge_cases = []
        for int_size in self.int_sizes:
            edge_cases.append("\x00" * int_size)
            edge_cases.append("\xFF" * int_size)
            edge_cases.append("\x7F" + ("\xFF" * (int_size - 1)))
            edge_cases.append(("\xFF" * (int_size - 1)) + "\x7F")
        return edge_cases

    def integer_tests(self):
        self.value = copy.deepcopy(self.original_value)
        m_value = self.render()

        if self.edge_case_cnt > len(self.edge_cases) - 1:
            self.i_position += 1
            self.edge_case_cnt = 0

        temp = []
        for x in m_value[:self.i_position] +\
                 self.edge_cases[self.edge_case_cnt] +\
                 m_value[self.i_position+len(self.edge_cases[self.edge_case_cnt]):]:
            temp.append(ord(x))
        self.value = copy.deepcopy(temp)

        self.edge_case_cnt += 1
        self.mutant_index += 1

        return True

    def mutate (self):
        self.value = copy.deepcopy(self.original_value)

        if not self.fuzzable or self.fuzz_complete:
            self.value = copy.deepcopy(self.original_value)
            return False

        if self.mutant_index == self.num_mutations():
            self.value = copy.deepcopy(self.original_value)
            self.fuzz_complete = True
            return False

        if self.byte_replace():
            return True
        return self.integer_tests()

    def num_mutations (self):
        # calculate the mutations for single-byte mutations.
        mutations = (len(self.original_value) * len(self.payloads))

        # update the number of mutations additional test cases
        for position in range(0, len(self.original_value)):
            for edge_case in self.edge_cases:
                mutations += 1
        return mutations

    def render (self):
        self.rendered = ""
        for r_byte in self.value:
            self.rendered += chr(r_byte)
        return self.rendered

# =============================================================================
#
# =============================================================================

class string (base_primitive):
    # store fuzz_library as a class variable to avoid copying the ~70MB structure across each instantiated primitive.
    fuzz_library = []

    def __init__ (self, value, size=-1, padding="\x00", encoding="ascii", compression=None, fuzzable=True, max_len=0, name=None):
        '''
        Primitive that cycles through a library of "bad" strings. The class variable 'fuzz_library' contains a list of
        smart fuzz values global across all instances. The 'this_library' variable contains fuzz values specific to
        the instantiated primitive. This allows us to avoid copying the near ~70MB fuzz_library data structure across
        each instantiated primitive.

        @type  value:    String
        @param value:    Default string value
        @type  size:     Integer
        @param size:     (Optional, def=-1) Static size of this field, leave -1 for dynamic.
        @type  padding:  Character
        @param padding:  (Optional, def="\\x00") Value to use as padding to fill static field size.
        @type  encoding: String
        @param encoding: (Optonal, def="ascii") String encoding, ex: utf_16_le for Microsoft Unicode.
        @type  compression: String
        @param compression: (Optonal, def=None) String compression, ex: zlib.
        @type  fuzzable: Boolean
        @param fuzzable: (Optional, def=True) Enable/disable fuzzing of this primitive
        @type  max_len:  Integer
        @param max_len:  (Optional, def=0) Maximum string length
        @type  name:     String
        @param name:     (Optional, def=None) Specifying a name gives you direct access to a primitive
        '''

        self.value         = self.original_value = value
        self.size          = size
        self.padding       = padding
        self.encoding      = encoding
        self.compression   = compression
        self.fuzzable      = fuzzable
        self.name          = name

        self.s_type        = "string"  # for ease of object identification
        self.rendered      = ""        # rendered value
        self.fuzz_complete = False     # flag if this primitive has been completely fuzzed
        self.mutant_index  = 0         # current mutation number

        if not value:
            raise sex.SullyRuntimeError("'%s' primitive requires a default value" % self.s_type)
        if name and not type(name) is str:
            raise sex.SullyRuntimeError("'%s' primitive name has to be of type str" % self.s_type)
        if fuzzable != True and fuzzable != False:
            raise sex.SullyRuntimeError("'%s' primitive requires fuzzable to be of type boolean" % self.s_type)
        if not type(size) is int:
            raise sex.SullyRuntimeError("'%s' primitive size has to be of type int" % self.s_type)
        if not type(padding) is str:
            raise sex.SullyRuntimeError("'%s' primitive padding has to be of type str" % self.s_type)
        if not type(encoding) is str:
            raise sex.SullyRuntimeError("'%s' primitive encoding has to be of type str" % self.s_type)
        if compression and not type(compression) is str:
            raise sex.SullyRuntimeError("'%s' primitive compression has to be of type str" % self.s_type)
        if not type(max_len) is int:
            raise sex.SullyRuntimeError("'%s' primitive max_len has to be of type int" % self.s_type)

        # add this specific primitives repitition values to the unique fuzz library.
        self.this_library = \
        [
            self.value * 2,
            self.value * 10,
            self.value * 100,

            # UTF-8
            self.value * 2   + "\xfe",
            self.value * 10  + "\xfe",
            self.value * 100 + "\xfe",
        ]

        # if the fuzz library has not yet been initialized, do so with all the global values.
        if not self.fuzz_library:
            string.fuzz_library  = \
            [
                # omission.
                "",

                # strings ripped from spike (and some others I added)
                "/.:/"  + "A"*5000 + "\x00\x00",
                "/.../" + "A"*5000 + "\x00\x00",
                "/.../.../.../.../.../.../.../.../.../.../",
                "/../../../../../../../../../../../../etc/passwd",
                "/../../../../../../../../../../../../boot.ini",
                "..:..:..:..:..:..:..:..:..:..:..:..:..:",
                "\\\\*",
                "\\\\?\\",
                "/\\" * 5000,
                "/." * 5000,
                "!@#$%%^#$%#$@#$%$$@#$%^^**(()",
                "%01%02%03%04%0a%0d%0aADSF",
                "%01%02%03@%04%0a%0d%0aADSF",
                "/%00/",
                "%00/",
                "%00",
                "%u0000",
                "%\xfe\xf0%\x00\xff",
                "%\xfe\xf0%\x01\xff" * 20,

                # format strings.
                "%n"     * 100,
                "%n"     * 500,
                "\"%n\"" * 500,
                "%s"     * 100,
                "%s"     * 500,
                "\"%s\"" * 500,

                # command injection.
                "|touch /tmp/SULLEY",
                ";touch /tmp/SULLEY;",
                "|notepad",
                ";notepad;",
                "\nnotepad\n",

                # SQL injection.
                "1;SELECT%20*",
                "'sqlattempt1",
                "(sqlattempt2)",
                "OR%201=1",

                # some binary strings.
                "\xde\xad\xbe\xef",
                "\xde\xad\xbe\xef" * 10,
                "\xde\xad\xbe\xef" * 100,
                "\xde\xad\xbe\xef" * 1000,
                "\xde\xad\xbe\xef" * 10000,
                "\x00"             * 1000,

                # miscellaneous.
                "\r\n" * 100,
                "<>" * 500,         # sendmail crackaddr (http://lsd-pl.net/other/sendmail.txt)
            ]

            # Add some long strings
            longs = ["A", "B", "1", "2", "3", "<", ">", "'", "\"", "/", "\\", "?",
                     "=", "a=", "&", ".", ",", "(", ")", "]", "[", "%", "*", "-",
                     "_", "+", "{", "}", "%s", "%d", "%n", "\x14", "\xFE", "\xFF"]

            for to_long in longs:
                self.add_long_strings(to_long)

            # add some long strings with null bytes thrown in the middle of it.
            for length in [128, 256, 1024, 2048, 4096, 10000, 15000, 20000, 25000, 32767, 50000, 0xFFFF]:
                s = "B" * length
                s = s[:len(s)/2] + "\x00" + s[len(s)/2:]
                string.fuzz_library.append(s)

            # if the optional file '.fuzz_strings' is found, parse each line as a new entry for the fuzz library.
            try:
                fh = open(".fuzz_strings", "r")

                for fuzz_string in fh.readlines():
                    fuzz_string = fuzz_string.rstrip("\r\n")

                    if fuzz_string != "":
                        string.fuzz_library.append(fuzz_string)

                fh.close()
            except:
                pass

        # delete strings which length is greater than max_len.
        if max_len > 0:
            if any(len(s) > max_len for s in self.this_library):
                self.this_library = list(set([s[:max_len] for s in self.this_library]))

            if any(len(s) > max_len for s in self.fuzz_library):
                self.fuzz_library = list(set([s[:max_len] for s in self.fuzz_library]))


    def add_long_strings (self, sequence):
        '''
        Given a sequence, generate a number of selectively chosen strings lengths of the given sequence and add to the
        string heuristic library.

        @type  sequence: String
        @param sequence: Sequence to repeat for creation of fuzz strings.
        '''

        for length in [128, 255, 256, 257, 511, 512, 513, 1023, 1024, 2048, 2049, 4095, 4096, 4097, 5000, 10000, 15000,
                       20000, 25000, 32762, 32763, 32764, 32765, 32766, 32767, 32768, 32769, 0xFFFF-2, 0xFFFF-1,
                       0xFFFF, 0xFFFF+1, 0xFFFF+2, 99999, 100000, 500000, 1000000]:

            long_string = sequence * length
            string.fuzz_library.append(long_string)


    def mutate (self):
        '''
        Mutate the primitive by stepping through the fuzz library extended with the "this" library, return False on
        completion.

        @rtype:  Boolean
        @return: True on success, False otherwise.
        '''

        # loop through the fuzz library until a suitable match is found.
        while 1:
            # if we've ran out of mutations, raise the completion flag.
            if self.mutant_index == self.num_mutations():
                self.fuzz_complete = True

            # if fuzzing was disabled or complete, and mutate() is called, ensure the original value is restored.
            if not self.fuzzable or self.fuzz_complete:
                self.value = self.original_value
                return False

            # update the current value from the fuzz library.
            self.value = (self.fuzz_library + self.this_library)[self.mutant_index]

            # increment the mutation count.
            self.mutant_index += 1

            # if the size parameter is disabled, break out of the loop right now.
            if self.size == -1:
                break

            # ignore library items greather then user-supplied length.
            if len(self.value) > self.size: self.value = self.value[0:self.size]

            # pad undersized library items.
            if len(self.value) < self.size:
                self.value = self.value + self.padding * (self.size - len(self.value))
                break

        return True


    def num_mutations (self):
        '''
        Calculate and return the total number of mutations for this individual primitive.

        @rtype:  Integer
        @return: Number of mutated forms this primitive can take
        '''

        return len(self.fuzz_library) + len(self.this_library)


    def render (self):
        '''
        Render the primitive, encode the string according to the specified encoding.
        '''

        if self.compression == "zlib":
            try:
                self.rendered = zlib.compress(str(self.value))
            except:
                self.rendered = self.value

        # try to encode the string properly and fall back to the default value on failure.
        try:
            self.rendered = str(self.value).encode(self.encoding)
        except:
            self.rendered = self.value

        return self.rendered

# =============================================================================
#
# =============================================================================

class bit_field (base_primitive):
    def __init__ (self, value, width, max_num=None, endian="<", format="binary", signed=False, full_range=False, fuzzable=True, name=None, synchsafe=False):
        '''
        The bit field primitive represents a number of variable length and is used to define all other integer types.

        @type  value:      Integer
        @param value:      Default integer value
        @type  width:      Integer
        @param width:      Width of bit fields
        @type  endian:     Character
        @param endian:     (Optional, def=LITTLE_ENDIAN) Endianess of the bit field (LITTLE_ENDIAN: <, BIG_ENDIAN: >)
        @type  format:     String
        @param format:     (Optional, def=binary) Output format, "binary" or "ascii"
        @type  signed:     Boolean
        @param signed:     (Optional, def=False) Make size signed vs. unsigned (applicable only with format="ascii")
        @type  full_range: Boolean
        @param full_range: (Optional, def=False) If enabled the field mutates through *all* possible values.
        @type  fuzzable:   Boolean
        @param fuzzable:   (Optional, def=True) Enable/disable fuzzing of this primitive
        @type  name:       String
        @param name:       (Optional, def=None) Specifying a name gives you direct access to a primitive
        @type  synchsafe:  Boolean
        @param synchsafe: (Optional, def=False) Synchsafe (https://en.wikipedia.org/wiki/Synchsafe)
        '''

        self.s_type = "bit_field"

        if not type(value) is long and not type(value) is int:
            raise sex.SullyRuntimeError("'%s' primitive requires value to be of type long, got: %s" % (self.s_type, str(type(value))))
        if name and not type(name) is str:
            raise sex.SullyRuntimeError("'%s' primitive name has to be of type str" % self.s_type)
        if fuzzable != True and fuzzable != False:
            raise sex.SullyRuntimeError("'%s' primitive requires fuzzable to be of type boolean" % self.s_type)
        if not type(width) is int:
            raise sex.SullyRuntimeError("'%s' primitive width has to be of type int" % self.s_type)
        if max_num and not type(max_num) is int:
            raise sex.SullyRuntimeError("'%s' primitive max_len has to be of type int" % self.s_type)
        if endian != ">" and endian != "<":
            raise sex.SullyRuntimeError("'%s' primitive endian has to be of '>' or '<'" % self.s_type)
        if not type(format) is str:
            raise sex.SullyRuntimeError("'%s' primitive format has to be of type str" % self.s_type)
        if signed != True and signed != False:
            raise sex.SullyRuntimeError("'%s' primitive requires signed to be of type boolean" % self.s_type)
        if full_range != True and full_range != False:
            raise sex.SullyRuntimeError("'%s' primitive requires full_range to be of type boolean" % self.s_type)
        if synchsafe != True and synchsafe != False:
            raise sex.SullyRuntimeError("'%s' primitive requires synchsafe to be of type boolean" % self.s_type)

        if type(value) in [int, long, list, tuple]:
            # TODO: synchsafe each item here overwriting value
            if type(value) in [int, long]:
                if synchsafe: value = self.t_synchsafe(value)
            if type(value) in [list]:
                cnt = 0
                for v in value:
                    if synchsafe:
                        value[cnt] = self.t_synchsafe(v)
                    else:
                        value[cnt] = v
                    cnt += 1
            if type(value) in [tuple]:
                value = list(value)
                cnt = 0
                for v in value:
                    if synchsafe:
                        value[cnt] = self.t_synchsafe(v)
                    else:
                        value[cnt] = v
                    cnt += 1
                value = tuple(value)
            self.value         = self.original_value = value
        else:
            raise AssertionError()

        self.width         = width
        self.max_num       = max_num
        self.endian        = endian
        self.format        = format
        self.signed        = signed
        self.full_range    = full_range
        self.fuzzable      = fuzzable
        self.name          = name

        self.rendered      = ""        # rendered value
        self.fuzz_complete = False     # flag if this primitive has been completely fuzzed
        self.fuzz_library  = []        # library of fuzz heuristics
        self.mutant_index  = 0         # current mutation number

        if self.max_num == None:
            self.max_num = self.to_decimal("1" + "0" * width)

        assert(type(self.max_num) is int or type(self.max_num) is long)


        # build the fuzz library.
        if self.full_range:
            # add all possible values.
            for i in xrange(0, self.max_num):
                self.fuzz_library.append(i)
        else:
            if type(value) in [list, tuple]:
                # Use the supplied values as the fuzz library.
                for val in value:
                    self.fuzz_library.append(val)
            else:
                # try only "smart" values.
                self.add_integer_boundaries(0)
                self.add_integer_boundaries(self.max_num / 2)
                self.add_integer_boundaries(self.max_num / 3)
                self.add_integer_boundaries(self.max_num / 4)
                self.add_integer_boundaries(self.max_num / 8)
                self.add_integer_boundaries(self.max_num / 16)
                self.add_integer_boundaries(self.max_num / 32)
                self.add_integer_boundaries(self.max_num)

        # if the optional file '.fuzz_ints' is found, parse each line as a new entry for the fuzz library.
        try:
            fh = open(".fuzz_ints", "r")

            for fuzz_int in fh.readlines():
                # convert the line into an integer, continue on failure.
                try:
                    fuzz_int = long(fuzz_int, 16)
                except:
                    continue

                if fuzz_int < self.max_num:
                    self.fuzz_library.append(fuzz_int)

            fh.close()
        except:
            pass

    def t_synchsafe(self, integer):
        out = mask = 0x7F
        while (mask ^ 0x7FFFFFFF):
            out = integer & ~mask
            out <<= 1
            out |= integer & mask
            mask = ((mask + 1) << 8) - 1
            integer = out
        return out

    def add_integer_boundaries (self, integer):
        '''
        Add the supplied integer and border cases to the integer fuzz heuristics library.

        @type  integer: Int
        @param integer: Integer to append to fuzz heuristics
        '''

        for i in xrange(-10, 10):
            case = integer + i

            # ensure the border case falls within the valid range for this field.
            if 0 <= case < self.max_num:
                if case not in self.fuzz_library:
                    self.fuzz_library.append(case)


    def render (self):
        '''
        Render the primitive.
        '''

        #
        # binary formatting.
        #

        if self.format == "binary":
            bit_stream = ""
            rendered   = ""

            # pad the bit stream to the next byte boundary.
            if self.width % 8 == 0:
                bit_stream += self.to_binary()
            else:
                bit_stream  = "0" * (8 - (self.width % 8))
                bit_stream += self.to_binary()

            # convert the bit stream from a string of bits into raw bytes.
            for i in xrange(len(bit_stream) / 8):
                chunk = bit_stream[8*i:8*i+8]
                rendered += struct.pack("B", self.to_decimal(chunk))

            # if necessary, convert the endianess of the raw bytes.
            if self.endian == "<":
                rendered = list(rendered)
                rendered.reverse()
                rendered = "".join(rendered)

            self.rendered = rendered

        #
        # ascii formatting.
        #

        else:
            # if the sign flag is raised and we are dealing with a signed integer (first bit is 1).
            if self.signed and self.to_binary()[0] == "1":

                max_num = self.to_decimal("1" + "0" * (self.width - 1))
                # mask off the sign bit.
                val = self.value & self.to_decimal("1" * (self.width - 1))

                # account for the fact that the negative scale works backwards.
                val = max_num - val - 1

                # toss in the negative sign.
                self.rendered = "%d" % ~val

            # unsigned integer or positive signed integer.
            else:
                self.rendered = "%d" % self.value

        return self.rendered


    def to_binary (self, number=None, bit_count=None):
        '''
        Convert a number to a binary string.

        @type  number:    Integer
        @param number:    (Optional, def=self.value) Number to convert
        @type  bit_count: Integer
        @param bit_count: (Optional, def=self.width) Width of bit string

        @rtype:  String
        @return: Bit string
        '''

        if number == None:
            if type(self.value) in [list, tuple]:
                # We have been given a list to cycle through that is not being mutated...
                if self.cyclic_index == len(self.value):
                    # Reset the index.
                    self.cyclic_index = 0
                number = self.value[self.cyclic_index]
                self.cyclic_index += 1
            else:
                number = self.value

        if bit_count == None:
            bit_count = self.width

        return "".join(map(lambda x:str((number >> x) & 1), range(bit_count -1, -1, -1)))

    def to_decimal (self, binary):
        '''
        Convert a binary string to a decimal number.

        @type  binary: String
        @param binary: Binary string

        @rtype:  Integer
        @return: Converted bit string
        '''

        return int(binary, 2)

# =============================================================================
#
# =============================================================================

class byte (bit_field):
    def __init__ (self, value, endian="<", format="binary", synchsafe=False, signed=False, full_range=False, fuzzable=True, name=None):
        self.s_type  = "byte"

        if name and not type(name) is str:
            raise sex.SullyRuntimeError("'%s' primitive name has to be of type str" % self.s_type)
        if fuzzable != True and fuzzable != False:
            raise sex.SullyRuntimeError("'%s' primitive requires fuzzable to be of type boolean" % self.s_type)
        if endian != ">" and endian != "<":
            raise sex.SullyRuntimeError("'%s' primitive endian has to be of '>' or '<'" % self.s_type)
        if not type(format) is str:
            raise sex.SullyRuntimeError("'%s' primitive format has to be of type str" % self.s_type)
        if signed != True and signed != False:
            raise sex.SullyRuntimeError("'%s' primitive requires signed to be of type boolean" % self.s_type)
        if full_range != True and full_range != False:
            raise sex.SullyRuntimeError("'%s' primitive requires full_range to be of type boolean" % self.s_type)
        if synchsafe != True and synchsafe != False:
            raise sex.SullyRuntimeError("'%s' primitive requires synchsafe to be of type boolean" % self.s_type)

        if type(value) not in [int, long, list, tuple]:
            value       = struct.unpack(endian + "B", value)[0]

        bit_field.__init__(self, value, 8, None, endian, format, signed, full_range, fuzzable, name, synchsafe)

# =============================================================================
#
# =============================================================================

class word (bit_field):
    def __init__ (self, value, endian="<", format="binary", synchsafe=False, signed=False, full_range=False, fuzzable=True, name=None):
        self.s_type  = "word"

        if name and not type(name) is str:
            raise sex.SullyRuntimeError("'%s' primitive name has to be of type str" % self.s_type)
        if fuzzable != True and fuzzable != False:
            raise sex.SullyRuntimeError("'%s' primitive requires fuzzable to be of type boolean" % self.s_type)
        if endian != ">" and endian != "<":
            raise sex.SullyRuntimeError("'%s' primitive endian has to be of '>' or '<'" % self.s_type)
        if not type(format) is str:
            raise sex.SullyRuntimeError("'%s' primitive format has to be of type str" % self.s_type)
        if signed != True and signed != False:
            raise sex.SullyRuntimeError("'%s' primitive requires signed to be of type boolean" % self.s_type)
        if full_range != True and full_range != False:
            raise sex.SullyRuntimeError("'%s' primitive requires full_range to be of type boolean" % self.s_type)
        if synchsafe != True and synchsafe != False:
            raise sex.SullyRuntimeError("'%s' primitive requires synchsafe to be of type boolean" % self.s_type)

        if type(value) not in [int, long, list, tuple]:
            value = struct.unpack(endian + "H", value)[0]

        bit_field.__init__(self, value, 16, None, endian, format, signed, full_range, fuzzable, name, synchsafe)

# =============================================================================
#
# =============================================================================

class dword (bit_field):
    def __init__ (self, value, endian="<", format="binary", synchsafe=False, signed=False, full_range=False, fuzzable=True, name=None):
        self.s_type  = "dword"

        if name and not type(name) is str:
            raise sex.SullyRuntimeError("'%s' primitive name has to be of type str" % self.s_type)
        if fuzzable != True and fuzzable != False:
            raise sex.SullyRuntimeError("'%s' primitive requires fuzzable to be of type boolean" % self.s_type)
        if endian != ">" and endian != "<":
            raise sex.SullyRuntimeError("'%s' primitive endian has to be of '>' or '<'" % self.s_type)
        if not type(format) is str:
            raise sex.SullyRuntimeError("'%s' primitive format has to be of type str" % self.s_type)
        if signed != True and signed != False:
            raise sex.SullyRuntimeError("'%s' primitive requires signed to be of type boolean" % self.s_type)
        if full_range != True and full_range != False:
            raise sex.SullyRuntimeError("'%s' primitive requires full_range to be of type boolean" % self.s_type)
        if synchsafe != True and synchsafe != False:
            raise sex.SullyRuntimeError("'%s' primitive requires synchsafe to be of type boolean" % self.s_type)

        if type(value) not in [int, long, list, tuple]:
            value = struct.unpack(endian + "L", value)[0]

        bit_field.__init__(self, value, 32, None, endian, format, signed, full_range, fuzzable, name, synchsafe)

# =============================================================================
#
# =============================================================================

class qword (bit_field):
    def __init__ (self, value, endian="<", format="binary", synchsafe=False, signed=False, full_range=False, fuzzable=True, name=None):
        self.s_type  = "qword"

        if name and not type(name) is str:
            raise sex.SullyRuntimeError("'%s' primitive name has to be of type str" % self.s_type)
        if fuzzable != True and fuzzable != False:
            raise sex.SullyRuntimeError("'%s' primitive requires fuzzable to be of type boolean" % self.s_type)
        if endian != ">" and endian != "<":
            raise sex.SullyRuntimeError("'%s' primitive endian has to be of '>' or '<'" % self.s_type)
        if not type(format) is str:
            raise sex.SullyRuntimeError("'%s' primitive format has to be of type str" % self.s_type)
        if signed != True and signed != False:
            raise sex.SullyRuntimeError("'%s' primitive requires signed to be of type boolean" % self.s_type)
        if full_range != True and full_range != False:
            raise sex.SullyRuntimeError("'%s' primitive requires full_range to be of type boolean" % self.s_type)
        if synchsafe != True and synchsafe != False:
            raise sex.SullyRuntimeError("'%s' primitive requires synchsafe to be of type boolean" % self.s_type)

        if type(value) not in [int, long, list, tuple]:
            value = struct.unpack(endian + "Q", value)[0]

        bit_field.__init__(self, value, 64, None, endian, format, signed, full_range, fuzzable, name, synchsafe)

# =============================================================================
#
# =============================================================================

class bitfield (base_primitive):
    '''
    Create a bitfield which defines a value as fields of bits.
    A bit fields item looks like e.g.: {"width": 11, "value": 0b11111111111, "name": "FRAME_SYNC"}
    By default fields are non-fuzzable so to fuzz them fuzzable parameter should be
    explicitly set to True.

    Bits are added from left to right, this means the first bitfield is at the left and subsequent fields are
    added at it's right.
    If the resulting value (concatenated bit fields) is less than _length_ long the value gets padded with 0 bits
    at the left.
    '''

    def __init__ (self, value, request, length, fuzzable, fields=[], name=None):
        '''
        @type  name:       String
        @param name:       Name of the bitfield
        @type  request:    s_request
        @param request:    Request this block belongs to
        @type  fields:     List
        @param fields:     List of bit fields defining the value
        '''

        self.value = self.original_value = value
        self.name                = name
        self.request             = request

        self.length              = length
        self.field_index         = 0
        self.current_field       = ""
        self.mutant_index        = 0
        self.field_mutant_index  = 0
        self.current_field_index = 0
        self.sub_mutant_index    = 0
        self.fuzz_complete       = False
        self.s_type              = "bitfield"   # for ease of object identification
        self.rendered            = ""
        self.fuzzable            = fuzzable

        if not value:
            raise sex.SullyRuntimeError("'%s' primitive requires a default value" % self.s_type)
        if name and not type(name) is str:
            raise sex.SullyRuntimeError("'%s' primitive name has to be of type str" % self.s_type)
        if fuzzable != True and fuzzable != False:
            raise sex.SullyRuntimeError("'%s' primitive requires fuzzable to be of type boolean" % self.s_type)
        if not type(length) is int:
            raise sex.SullyRuntimeError("'%s' primitive requires length to be of type int" % self.s_type)
        if not type(fields) is list:
            raise sex.SullyRuntimeError("'%s' primitive requires fields to be of type list" % self.s_type)

        for field in fields:
            if not field.get("fuzzable"):
                field["fuzzable"] = False

        self.fields              = fields
        self.gen_mutations()

    '''
     Mutations:
         - set all bits to 0     - 1 mutation
         - set all bits to 1     - 1 mutation
         - inverse all bits      - 1 mutation
         - bit flipping          - <num_of_bits> mutation
           flip each bit position to the oppositve value at each iteration

         - bit 1 by one          - <num_of_bits> mutation
           at each iteration set all bits to 0 and turn the next bit to 1

         - bit 0 by one          - <num_of_bits> mutation
           at each iteration set all bits to 1 and turn the next bit to 0
    '''

    def not_(self, x):
        assert x in (0, 1)
        return abs(1-x)

    def pad_to_width(self, value, width):
        s_val = bin(value)[2:]
        return ("0" * (width - len(s_val))) + s_val

    def inverse_bits(self, value):
        new = ""
        for bit in value:
            new += str(self.not_(int(bit)))
        return new

    def gen_mutations (self):
        for field in self.fields:

            field["mutations"] = []

            # if field is not fuzzable, we skip it
            if not field["fuzzable"]: continue

            width = field["end"] - field["start"]
            val = "0" * ((self.length * 8) - len(bin(self.original_value)[2:])) + bin(self.original_value)[2:]

            # set all bits to 0
            field["mutations"].append("0" * width)
            #set all bits to 1
            field["mutations"].append("1" * width)
            # inverse all bits
            field["mutations"].append(self.inverse_bits(val[field["start"]:field["end"]]))

            # bit flipping
            b_value = val[field["start"]:field["end"]]
            counter = 0
            for bf_bit in b_value:
                n_bit = bin(self.not_(int(bf_bit)))[2:]
                field["mutations"].append(b_value[:counter] + n_bit + b_value[counter + 1:])
                counter += 1

            b_value = "0" * width
            counter = 0
            for bf_bit in b_value:
                n_bit = bin(self.not_(int(bf_bit)))[2:]
                field["mutations"].append(b_value[:counter] + n_bit + b_value[counter + 1:])
                counter += 1

            b_value = "1" * width
            counter = 0
            for bf_bit in b_value:
                n_bit = bin(self.not_(int(bf_bit)))[2:]
                field["mutations"].append(b_value[:counter] + n_bit + b_value[counter + 1:])
                counter += 1

            # Get only unique mutations
            field["mutations"] = list(set(field["mutations"]))

    def num_mutations (self):
        num = 0
        for field in self.fields:
            num += len(field["mutations"])
        return num

    def get_num_fuzzable_fields(self):
        total = 0
        for field in self.fields:
            if field["fuzzable"]: total += 1
        return total

    def mutate (self):
        # if we've ran out of mutations, raise the completion flag.
        if self.mutant_index == self.num_mutations():
            self.fuzz_complete = True

        # if fuzzing was disabled or complete, and mutate() is called, ensure the original value is restored.
        if not self.fuzzable or self.fuzz_complete:
            self.value = self.original_value
            return False

        # If the mutations of the current field are exhaused, move to the next field

        if self.sub_mutant_index >= len(self.fields[self.current_field_index]["mutations"]):
            self.sub_mutant_index = 0
            self.field_mutant_index += 1
            self.current_field_index += 1

        # If the current field does not have any mutations, move to the next field

        if len(self.fields[self.current_field_index]["mutations"]) == 0:
            while len(self.fields[self.current_field_index]["mutations"]) == 0:
                self.current_field_index += 1
                self.sub_mutant_index = 0

        # If no more fields to fuzz, then stop fuzzing

        if self.field_mutant_index > self.get_num_fuzzable_fields():
            self.value = self.original_value
            self.fuzz_complete = True
            return False

        self.current_field = ""
        if self.fields[self.current_field_index].get("name"):
            self.current_field = self.fields[self.current_field_index]["name"]

        f_s = self.fields[self.current_field_index]["start"]
        f_e = self.fields[self.current_field_index]["end"]
        width = f_e - f_s
        mutation = self.fields[self.current_field_index]["mutations"][self.sub_mutant_index]
        s_val = ("0" * ((self.length * 8) - len(bin(self.original_value)[2:]))) + bin(self.original_value)[2:]
        t_val = s_val[:f_s] + mutation + s_val[f_e:]
        self.value = int(t_val, 2)

        # increment the mutation count.
        self.sub_mutant_index += 1
        self.mutant_index += 1
        return True

    def render (self):
        self.rendered = ""

        req_width = (self.length * 8)
        r_value = bin(self.value)[2:]
        r_value = "0" * (req_width - len(r_value)) + r_value

        count = 0
        while count != self.length:
            self.rendered += struct.pack("B", int(r_value[count * 8:(count * 8) + 8], 2))
            count += 1

        return self.rendered

# =============================================================================
#
# =============================================================================

class padding:

    def __init__ (self, block_name, request, pad_byte=0x00, byte_align=4, max_reps=16, step=1, fuzzable=True, name=None):
        self.block_name         = block_name
        self.request            = request
        self.pad_byte           = pad_byte
        self.byte_align         = byte_align
        self.max_reps           = max_reps
        self.step               = step
        self.fuzzable           = fuzzable
        self.name               = name

        self.s_type             = "padding"
        self.value              = self.original_value = ""   # default to nothing!
        self.rendered           = ""                         # rendered value
        self.fuzz_complete      = False                      # flag if this primitive has been completely fuzzed
        self.fuzz_library       = []                         # library of static fuzz heuristics to cycle through.
        self.mutant_index       = 0                          # current mutation number

        if not block_name:
            raise sex.SullyRuntimeError("'%s' primitive requires a block_name" % self.s_type)
        if name and not type(name) is str:
            raise sex.SullyRuntimeError("'%s' primitive name has to be of type str" % self.s_type)
        if fuzzable != True and fuzzable != False:
            raise sex.SullyRuntimeError("'%s' primitive requires fuzzable to be of type boolean" % self.s_type)
        if not type(byte_align) is int:
            raise sex.SullyRuntimeError("'%s' primitive requires byte_align to be of type int" % self.s_type)
        if not type(max_reps) is int:
            raise sex.SullyRuntimeError("'%s' primitive requires max_reps to be of type int" % self.s_type)
        if not type(step) is int:
            raise sex.SullyRuntimeError("'%s' primitive requires step to be of type int" % self.s_type)

        for p_round in range(0, (max_reps / step)):
            self.fuzz_library.append(struct.pack("B", self.pad_byte) * step)

    def num_mutations (self):
        return len(self.fuzz_library)

    def mutate (self):
        self.value = self.original_value

        # if we've run out of mutations, raise the completion flag.
        if self.mutant_index >= self.num_mutations():
            self.fuzz_complete = True

        # if fuzzing was disabled or complete, and mutate() is called, ensure the original value is restored.
        if not self.fuzzable or self.fuzz_complete:
            self.value = self.original_value
            return False

        self.value = self.fuzz_library[self.mutant_index]

        # increment the mutation count.
        self.mutant_index += 1

        return True

    def render (self):
        try:
            block = self.request.closed_blocks[self.block_name].rendered
        except KeyError, kex:
            raise sex.SullyRuntimeError("padding primitive could not find closed block '%s', exception: %s" % (self.block_name, str(kex)))
        except Exception, ex:
            raise sex.SullyRuntimeError("padding primitive could not process block '%s', exception: %s" % (self.block_name, str(ex)))

        block_length = len(block)
        add_bytes = (self.byte_align - (block_length % self.byte_align)) % self.byte_align
        self.rendered = struct.pack("B", self.pad_byte) * add_bytes

        self.rendered += str(self.value)
        return self.rendered

    def reset (self):
        '''
        Reset the fuzz state of this primitive.
        '''

        self.fuzz_complete  = False
        self.mutant_index   = 0
        self.value          = self.original_value

