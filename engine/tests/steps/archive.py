from behave import *
import os
import sys
import inspect

ROOT_DIR = os.path.dirname(
                os.path.abspath(
                    inspect.getfile(inspect.currentframe()
                )))

sys.path.append(ROOT_DIR + "/../../classes")
sys.path.append(ROOT_DIR + "/../../modules/archivehandler")
from ConfigurationHandler import ConfigurationHandler
from archivehandler import archivehandler

@given('we have the archive handler initialized')
def step_impl(context):
    assert os.path.isfile(ROOT_DIR + "/../../etc/engine.config")
    context.root_dir = ROOT_DIR + "/../../"
    config_file      = ROOT_DIR + "/../../etc/engine.config"
    config_data      = ConfigurationHandler(config_file).get()
    context.ahandler = archivehandler(context.root_dir, config_data)
    assert context.ahandler


@when('we call the archive handler descriptor')
def step_impl(context):
    context.descriptor = context.ahandler.descriptor()

@then('we get the archive handler module descriptor')
def step_impl(context):
    assert type(context.descriptor) == dict
    assert context.descriptor.get('version')
    assert context.descriptor.get('type')
    assert context.descriptor.get('name')


@when('we retrieve the running status')
def step_impl(context):
    context.is_running = context.ahandler.is_running()

@then('we receive False as archive handler not running')
def step_impl(context):
    assert context.is_running == False


@when('we load the archived job data')
def step_impl(context):
    job_path = ROOT_DIR + "/archive.job"
    assert os.path.isfile(job_path)
    context.job_data = context.ahandler.load_job_data(job_path)

@then('we get a dictionary of job details')
def step_impl(context):
    assert type(context.job_data) == dict
    assert context.job_data.get('session')
    assert context.job_data.get('target')
    assert context.job_data.get('request')


@when('we ask for the list of archived jobs')
def step_impl(context):
    context.archived_jobs = context.ahandler.get_archived_jobs()

@then('we get a list of archived jobs')
def step_impl(context):
    assert type(context.archived_jobs) == list

