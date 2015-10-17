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
    assert context.ret_val == SESSION_DATA

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

