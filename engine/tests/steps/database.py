from behave import *
import os
import sys
import json
import time
import inspect

ROOT_DIR = os.path.dirname(
                os.path.abspath(
                    inspect.getfile(inspect.currentframe()
                )))

sys.path.append(ROOT_DIR + "/../../classes")
from ConfigurationHandler import ConfigurationHandler
from DatabaseHandler import DatabaseHandler

