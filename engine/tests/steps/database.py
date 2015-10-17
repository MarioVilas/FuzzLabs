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

sys.path.append(ROOT_DIR + "/../../")
from ConfigurationHandler import ConfigurationHandler
from classes.DatabaseHandler import DatabaseHandler

CONFIG_FILE = ROOT_DIR + "/../../etc/engine.config"
CONFIG      = ConfigurationHandler(CONFIG_FILE).get()
DATABASE    = DatabaseHandler(CONFIG, ROOT_DIR)

JOB_DATA = SESSION_DATA = {
    "job_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "data": "this is just test data"
}

ISSUE_DATA = {
    "job_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "mutant_index": 101,
    "target": {},
    "name": "TEST",
    "process_status": {},
    "request": "REQUEST DATA"
}
ISSUE_DATA_ID = "10708a964e6a54434d9853a2b1cff7bc0b564d51"

LOG_TIME = None

@given('we have session status data')
def step_impl(context):
    pass

@when('we save the session status data')
def step_impl(context):
    context.ret_val = DATABASE.saveSession(SESSION_DATA)

@then('true is returned if session data was saved')
def step_impl(context):
    assert context.ret_val

@given('we are connected to the database')
def step_impl(context):
    pass

@when('we load the session status data')
def step_impl(context):
    context.ret_val = DATABASE.loadSession(SESSION_DATA["job_id"])

@then('the session data is returned')
def step_impl(context):
    assert context.ret_val["job_id"] == SESSION_DATA["job_id"]
    assert context.ret_val["data"] == SESSION_DATA["data"]

@when('we delete the session status data')
def step_impl(context):
    context.ret_val = DATABASE.deleteSession(SESSION_DATA["job_id"])

@then('true is returned if the session data was deleted')
def step_impl(context):
    assert context.ret_val

@when('we update the session status data')
def step_impl(context):
    newdata = {
        "job_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "data": "this is just test data update"
    }

    context.ret_val = DATABASE.updateSession(SESSION_DATA["job_id"], newdata)

@then('true is returned if update was successful')
def step_impl(context):
    assert context.ret_val

@when('we retrieve the list of jobs')
def step_impl(context):
    context.ret_val = DATABASE.loadJobs()

@then('a job list is returned')
def step_impl(context):
    assert type(context.ret_val) == list

@when('we insert a job into the database')
def step_impl(context):
    context.ret_val = DATABASE.insertJob(JOB_DATA)

@then('true is returned if job was saved')
def step_impl(context):
    assert context.ret_val == True

@when('we load the job from the database')
def step_impl(context):
    context.ret_val = DATABASE.loadJob(JOB_DATA["job_id"])

@then('the job description is returned')
def step_impl(context):
    assert context.ret_val["job_id"] == JOB_DATA["job_id"]
    assert context.ret_val["data"] == JOB_DATA["data"]

@when('we update a job in the database')
def step_impl(context):
    context.ret_val = DATABASE.updateJob(JOB_DATA["job_id"],
                                         1,
                                         "TEST",
                                         0, 1, 2, 3)

@then('true is returned if job was updated')
def step_impl(context):
    assert context.ret_val == True

@when('we delete a job in the database')
def step_impl(context):
    context.ret_val = DATABASE.deleteJob(JOB_DATA["job_id"])

@then('true is returned if job was deleted')
def step_impl(context):
    assert context.ret_val == True

@when('we insert an issue into the database')
def step_impl(context):
    context.ret_val = DATABASE.saveIssue(ISSUE_DATA)

@then('the issue ID is returned if the issue was saved')
def step_impl(context):
    global ISSUE_DATA_ID
    ISSUE_DATA_ID = context.ret_val
    assert context.ret_val

@when('we load the issue from the database')
def step_impl(context):
    global ISSUE_DATA_ID
    context.ret_val = DATABASE.loadIssue(ISSUE_DATA_ID)

@then('the issue dictionary is returned')
def step_impl(context):
    assert type(context.ret_val) == dict
    context.ret_val["job_id"] == ISSUE_DATA["job_id"]

@when('we load the list of issues from the database')
def step_impl(context):
    context.ret_val = DATABASE.loadIssues()

@then('a list of issues is returned')
def step_impl(context):
    assert type(context.ret_val) == list
    assert len(context.ret_val) > 0

@when('we delete the issue from the database')
def step_impl(context):
    global ISSUE_DATA_ID
    context.ret_val = DATABASE.deleteIssue(ISSUE_DATA_ID)

@then('true is returned if the issue was deleted')
def step_impl(context):
    assert context.ret_val

@when('we log several events to the database')
def step_impl(context):
    global LOG_TIME
    LOG_TIME = time.time()
    context.ret_val = DATABASE.log(
        "info",
        "behave test message 1",
        None
    )
    if not context.ret_val: return

    context.ret_val = DATABASE.log(
        "debug",
        "behave test message 2",
        "behave debug test message debug info 2"
    )
    if not context.ret_val: return

    context.ret_val = DATABASE.log(
        "error",
        "behave test message 3",
        "behave debug test message debug info 3"
    )
    if not context.ret_val: return

    context.ret_val = DATABASE.log(
        "critical",
        "behave test message 4",
        "behave debug test message debug info 4"
    )
    if not context.ret_val: return

@then('true is returned if the events were logged')
def step_impl(context):
    assert context.ret_val

@when('we fetch the list of logs from database')
def step_impl(context):
    context.ret_val = DATABASE.loadLogs()

@then('a list of logs is returned')
def step_impl(context):
    assert type(context.ret_val) == list

@when('we get logs newer than timestamp from database')
def step_impl(context):
    global LOG_TIME
    context.ret_val = DATABASE.loadLogs(LOG_TIME)

@then('a list of logs newer than timestamp is returned')
def step_impl(context):
    assert type(context.ret_val) == list
    assert len(context.ret_val) > 0

