from behave import *
import os
import sys
import inspect

ROOT_DIR = os.path.dirname(
                os.path.abspath(
                    inspect.getfile(inspect.currentframe()
                )))

sys.path.append(ROOT_DIR + "/../../classes")
from ConfigurationHandler import ConfigurationHandler
from ModuleHandler import ModuleHandler

@given('we have root and config')
def step_impl(context):
    assert os.path.isfile(ROOT_DIR + "/../../etc/engine.config")
    context.root        = ROOT_DIR + "/../../"
    config_file         = ROOT_DIR + "/../../etc/engine.config"
    context.config_data = ConfigurationHandler(config_file).get()

@when('we load the modules')
def step_impl(context):
    context.module_inst = ModuleHandler(context.root, context.config_data)
    context.modules_list = context.module_inst.loaded_modules

@then('we get a list of modules')
def step_impl(context):
    status = type(context.modules_list) == list
    context.module_inst.unload_modules()

    if status:
        for module in context.modules_list:
            if not module.get('instance') or \
               not module.get('name') or \
               not module.get('mtime') or \
               not module.get('type'):
                status = False
                break

    assert status



@given('we have modules loaded')
def step_impl(context):
    assert os.path.isfile(ROOT_DIR + "/../../etc/engine.config")
    root_dir     = ROOT_DIR + "/../../"
    config_file  = ROOT_DIR + "/../../etc/engine.config"
    config_data  = ConfigurationHandler(config_file).get()
    context.module_inst = ModuleHandler(root_dir, config_data)
    context.modules_list = context.module_inst.loaded_modules

    status = type(context.modules_list) == list
    assert status

@when('we unload the modules')
def step_impl(context):
    context.module_inst.unload_modules()

@then('we get an empty list')
def step_impl(context):
    assert context.module_inst.loaded_modules == []

