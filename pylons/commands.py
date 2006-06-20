"""Paster Commands, for use with paster in your project

The command(s) listed here are for use with Paste to enable easy creation of
various core Pylons templates.

Currently available commands are::

    controller, shell
"""
import os
import os.path
import sys
import glob

from paste.script.command import Command, BadCommand
from paste.script.filemaker import FileOp
from paste.script import pluginlib, copydir
from paste.deploy import loadapp
import paste.fixture

class ControllerCommand(Command):
    """Create a Controller and functional test for it
    
    The Controller command will create the standard controller template
    file and associated functional test to speed creation of controllers.
    
    Example usage::
    
        yourproj% paster controller comments
        Creating yourproj/yourproj/controllers/comments.py
        Creating yourproj/yourproj/tests/functional/test_comments.py
    
    If you'd like to have controllers underneath a directory, just include
    the path as the controller name and the necessary directories will be
    created for you::
    
        yourproj% paster controller admin/trackback
        Creating yourproj/controllers/admin
        Creating yourproj/yourproj/controllers/admin/trackback.py
        Creating yourproj/yourproj/tests/functional/test_admin_trackback.py
    """
    summary = __doc__
    usage = 'CONTROLLER_NAME'
    
    min_args = 1
    max_args = 1
    group_name = 'pylons'
    
    parser = Command.standard_parser(simulate=True)
    parser.add_option('--no-test',
                      action='store_true',
                      dest='no_test',
                      help="Don't create the test; just the controller")

    def command(self):
        try:
            self.verbose = 3
            fo = FileOp(source_dir=os.path.join(os.path.dirname(__file__), 'templates'))
            try:
                name, dir = fo.parse_path_name_args(self.args[0])
            except:
                raise BadCommand('No egg_info directory was found')
            fullname = os.path.join(dir, name)
            if not fullname.startswith(os.sep): fullname = os.sep + fullname
            testname = fullname.replace(os.sep, '_')[1:]
            fo.template_vars.update({'name': name.title().replace('-', '_'),
                                  'fullname': fullname,
                                  'fname': os.path.join(dir, name),
                                  'lname': name})
            fo.copy_file(template='controller.py_tmpl',
                         dest=os.path.join('controllers', dir), filename=name)
            if not self.options.no_test:
                fo.copy_file(template='test_controller.py_tmpl',
                             dest=os.path.join('tests', 'functional'),
                             filename='test_'+testname)
        except:
            import sys
            msg = str(sys.exc_info()[1])
            raise BadCommand('An unknown error ocurred, %s' % msg)

class ShellCommand(Command):
    """Open an interactive shell with the Pylons app loaded
    
    Should include the name of the config file to use for the interactive
    shell. This allows you to test your mapper, models, and simulate
    web requests using ``paste.fixture``.
    
    Example::
        
        $ paster shell development.ini
    
    """
    summary = __doc__
    usage = 'CONFIG_FILE'
    
    min_args = 1
    max_args = 1
    group_name = 'pylons'
    
    parser = Command.standard_parser(simulate=True)

    def command(self):
        import sys
        self.verbose = 3
        config_name = 'config:%s' % self.args[0]
        here_dir = os.getcwd()
        locs = dict(__name__="pylons-admin")
        pkg_name = here_dir.split(os.path.sep)[-1].lower()
        
        # Load locals and populate with objects for use in shell
        sys.path.insert(0, here_dir)
        routing_package = pkg_name + '.config.routing'
        __import__(routing_package)
        make_map = getattr(sys.modules[routing_package], 'make_map')
        mapper = make_map()
        models_package = pkg_name + '.models'
        __import__(models_package)
        locs['model'] = sys.modules[models_package]
        from routes import url_for
        locs['mapper'] = mapper
        wsgiapp = loadapp(config_name, relative_to=here_dir)
        locs['wsgiapp'] = wsgiapp
        locs['app'] = paste.fixture.TestApp(wsgiapp)
        __import__(pkg_name + '.lib.helpers')
        locs['h'] = sys.modules[pkg_name + '.lib.helpers']
        
        banner = "Pylons Interactive Shell\nPython %s\n\n" % sys.version
        banner += "Additional Objects:\n\tmapper - Routes mapper object\n"
        banner += "\th - Helper object\n"
        banner += "\tmodel - Models from models package\n"
        banner += "\twsgiapp - This projects WSGI App instance\n"
        banner += "\tapp - paste.fixture wrapped around wsgiapp"
        try:
            # try to use IPython if possible
            import IPython
        
            class CustomIPShell(IPython.iplib.InteractiveShell):
                def raw_input(self, *args, **kw):
                    try:
                        return IPython.iplib.InteractiveShell.raw_input(self, *args, **kw)
                    except EOFError:
                        # In the future, we'll put our own override as needed to save
                        # models, TG style
                        raise EOFError

            shell = IPython.Shell.IPShell(user_ns=locs, shell_class=CustomIPShell)
            shell.mainloop()
        except ImportError:
            import code
            
            class CustomShell(code.InteractiveConsole):
                def raw_input(self, *args, **kw):
                    try:
                        return code.InteractiveConsole.raw_input(self, *args, **kw)
                    except EOFError:
                        # In the future, we'll put our own override as needed to save
                        # models, TG style
                        raise EOFError
            
            shell = CustomShell(locals=locs)
            shell.interact(banner)
