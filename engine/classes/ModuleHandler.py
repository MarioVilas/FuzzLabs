"""
Manage FuzzLabs modules.
"""

import os
import sys
import time
import syslog

class ModuleHandler():
    """
    Handle loading, unloading and reloading of modules.
    """

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __init__(self, root, config):
        """
        Initialize variables and modules.

        @type  root:     String
        @param root:     Full path to the FuzzLabs root directory
        @type  config:   Dictionary
        @param config:   The complete configuration as a dictionary
        """

        self.root = root
        self.config = config
        self.loaded_modules = []
        self.modules_dir = self.root + "/modules"
        syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)
        self.__init_modules()

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __init_modules(self):
        """
        Initial load of modules. All modules not already loaded will get
        initialized and started.
        """

        for module_name in self.get_directories():
            if self.is_module_loaded(module_name):
                continue

            mod = self.__load_module_by_name(module_name)
            if not mod:
                syslog.syslog(syslog.LOG_ERR,
                              'failed to load module: ' + \
                               module_name)
                continue

            try:
                mod["instance"].start()
                self.loaded_modules.append(mod)
            except Exception, ex:
                syslog.syslog(syslog.LOG_ERR,
                              'failed to start module: ' + \
                               mod["name"] + " (%s)" % str(ex))

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def get_directories(self):
        """
        Get the list of modules from the 'modules' directory.

        @rtype:          List
        @return:         List of module paths
        """


        dirs = []
        for entry in os.listdir(self.modules_dir):
            if not os.path.isfile(os.path.join(self.modules_dir, entry)): 
                dirs.append(entry)
        return dirs

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def is_module_loaded(self, name):
        """
        Check if a module is loaded by comparing _name_ with the name of the
        loaded modules from the list.

        @type  name:     String
        @param name:     Name of the module

        @rtype:          Boolean
        @return:         Whether the module has been loaded yet
        """

        for i, m_name in enumerate(m['name'] for m in self.loaded_modules):
            if name == m_name:
                return True
        return False

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def unload_modules(self):
        """
        Unload all modules.
        """

        unloaded = []
        for module in self.loaded_modules:
            try:
                while module["instance"].is_running():
                    module["instance"].stop()
                    time.sleep(1)
                unloaded.append(module)
            except Exception, ex:
                syslog.syslog(syslog.LOG_ERR,
                              'failed to stop module: ' + \
                              module["name"] + " (%s)" % str(ex))

        for module in unloaded:
            self.loaded_modules.remove(module)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __load_module_by_name(self, name):
        """
        Load a module specified by its name.

        @type  name:     String
        @param name:     Name of the module to be loaded

        @rtype:          Mixed
        @return:         None = not loaded, Dictionary = loaded module
        """

        syslog.syslog(syslog.LOG_INFO, "loading module " + name)
        module_dir = os.path.join(self.modules_dir, name)

        l_mod = None
        try:
            sys.path.append(module_dir)
            l_mod = reload(__import__(name, fromlist=[name]))
            sys.path.remove(module_dir)
        except Exception as ex:
            syslog.syslog(syslog.LOG_ERR,
                          "failed to import module " + name +\
                          " (%s)" % str(ex))
            sys.path.remove(module_dir)
            return None

        mod_details = None

        try:
            l_class = getattr(l_mod, name)
            l_inst = l_class(self.root, self.config)
            mod_details = l_inst.descriptor()
            mod_details["name"] = name
            mod_details["mtime"] = os.path.getmtime(self.modules_dir + "/" + \
                                                    name) * 1000000
            mod_details["instance"] = l_inst
        except Exception as ex:
            syslog.syslog(syslog.LOG_ERR,
                          "failed to load module " + name + " (%s)" % str(ex))
            return None

        syslog.syslog(syslog.LOG_INFO, "module loaded: " + str(mod_details))
        return mod_details

