import os
import sys
import tempfile
import shutil
import subprocess
import pkg_resources
import urllib2
import time
from cStringIO import StringIO

import pecan

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest  # noqa


def has_internet():
    try:
        urllib2.urlopen('http://google.com', timeout=1)
        return True
    except urllib2.URLError:
        pass  # pragma: no cover
    return False


class TestPecanScaffold(unittest.TestCase):

    def test_normalize_pkg_name(self):
        from pecan.scaffolds import PecanScaffold
        s = PecanScaffold()
        assert s.normalize_pkg_name('sam') == 'sam'
        assert s.normalize_pkg_name('sam1') == 'sam1'
        assert s.normalize_pkg_name('sam_') == 'sam_'
        assert s.normalize_pkg_name('Sam') == 'sam'
        assert s.normalize_pkg_name('SAM') == 'sam'
        assert s.normalize_pkg_name('sam ') == 'sam'
        assert s.normalize_pkg_name(' sam') == 'sam'
        assert s.normalize_pkg_name('sam$') == 'sam'
        assert s.normalize_pkg_name('sam-sam') == 'samsam'


class TestScaffoldUtils(unittest.TestCase):

    def setUp(self):
        self.scaffold_destination = tempfile.mkdtemp()
        self.out = sys.stdout

        sys.stdout = StringIO()

    def tearDown(self):
        shutil.rmtree(self.scaffold_destination)
        sys.stdout = self.out

    def test_copy_dir(self):
        from pecan.scaffolds import PecanScaffold

        class SimpleScaffold(PecanScaffold):
            _scaffold_dir = ('pecan', os.path.join(
                'tests', 'scaffold_fixtures', 'simple'
            ))

        SimpleScaffold().copy_to(os.path.join(
            self.scaffold_destination,
            'someapp'
        ), out_=StringIO())

        assert os.path.isfile(os.path.join(
            self.scaffold_destination, 'someapp', 'foo'
        ))
        assert os.path.isfile(os.path.join(
            self.scaffold_destination, 'someapp', 'bar', 'spam.txt'
        ))
        assert open(os.path.join(
            self.scaffold_destination, 'someapp', 'foo'
        ), 'r').read().strip() == 'YAR'
        assert open(os.path.join(
            self.scaffold_destination, 'someapp', 'foo'
        ), 'r').read().strip() == 'YAR'

    def test_destination_directory_levels_deep(self):
        from pecan.scaffolds import copy_dir
        f = StringIO()
        copy_dir(
            (
                'pecan', os.path.join('tests', 'scaffold_fixtures', 'simple')
            ),
            os.path.join(self.scaffold_destination, 'some', 'app'),
            {},
            out_=f
        )

        assert os.path.isfile(os.path.join(
            self.scaffold_destination, 'some', 'app', 'foo')
        )
        assert os.path.isfile(os.path.join(
            self.scaffold_destination, 'some', 'app', 'bar', 'spam.txt')
        )
        assert open(os.path.join(
            self.scaffold_destination, 'some', 'app', 'foo'
        ), 'r').read().strip() == 'YAR'
        assert open(os.path.join(
            self.scaffold_destination, 'some', 'app', 'bar', 'spam.txt'
        ), 'r').read().strip() == 'Pecan'

    def test_destination_directory_already_exists(self):
        from pecan.scaffolds import copy_dir
        from cStringIO import StringIO
        f = StringIO()
        copy_dir(
            (
                'pecan', os.path.join('tests', 'scaffold_fixtures', 'simple')
            ),
            os.path.join(self.scaffold_destination),
            {},
            out_=f
        )
        assert 'already exists' in f.getvalue()

    def test_copy_dir_with_filename_substitution(self):
        from pecan.scaffolds import copy_dir
        copy_dir(
            (
                'pecan', os.path.join('tests', 'scaffold_fixtures', 'file_sub')
            ),
            os.path.join(
                self.scaffold_destination, 'someapp'
            ),
            {'package': 'thingy'},
            out_=StringIO()
        )

        assert os.path.isfile(os.path.join(
            self.scaffold_destination, 'someapp', 'foo_thingy')
        )
        assert os.path.isfile(os.path.join(
            self.scaffold_destination, 'someapp', 'bar_thingy', 'spam.txt')
        )
        assert open(os.path.join(
            self.scaffold_destination, 'someapp', 'foo_thingy'
        ), 'r').read().strip() == 'YAR'
        assert open(os.path.join(
            self.scaffold_destination, 'someapp', 'bar_thingy', 'spam.txt'
        ), 'r').read().strip() == 'Pecan'

    def test_copy_dir_with_file_content_substitution(self):
        from pecan.scaffolds import copy_dir
        copy_dir(
            (
                'pecan',
                os.path.join('tests', 'scaffold_fixtures', 'content_sub'),
            ),
            os.path.join(
                self.scaffold_destination, 'someapp'
            ),
            {'package': 'thingy'},
            out_=StringIO()
        )

        assert os.path.isfile(os.path.join(
            self.scaffold_destination, 'someapp', 'foo')
        )
        assert os.path.isfile(os.path.join(
            self.scaffold_destination, 'someapp', 'bar', 'spam.txt')
        )
        assert open(os.path.join(
            self.scaffold_destination, 'someapp', 'foo'
        ), 'r').read().strip() == 'YAR thingy'
        assert open(os.path.join(
            self.scaffold_destination, 'someapp', 'bar', 'spam.txt'
        ), 'r').read().strip() == 'Pecan thingy'


class TestTemplateBuilds(unittest.TestCase):
    """
    Used to build and test the templated quickstart project(s).
    """

    install_dir = tempfile.mkdtemp()
    cwd = os.getcwd()

    def setUp(self):
        # Make a temp install location and record the cwd
        self.install_scaffolded_package()

    def tearDown(self):
        shutil.rmtree(self.install_dir)
        os.chdir(self.cwd)

    def create_virtualenv(self):
        # Create a new virtualenv in the temp install location
        import virtualenv
        virtualenv.create_environment(
            self.install_dir,
            site_packages=False
        )
        # chdir into the pecan source
        os.chdir(pkg_resources.get_distribution('pecan').location)

    def install_scaffolded_package(self):
        self.create_virtualenv()
        py_exe = os.path.join(self.install_dir, 'bin', 'python')
        pecan_exe = os.path.join(self.install_dir, 'bin', 'pecan')

        # env/bin/python setup.py develop (pecan)
        subprocess.check_call([
            py_exe,
            'setup.py',
            'develop'
        ])
        # create the templated project
        os.chdir(self.install_dir)
        subprocess.check_call([pecan_exe, 'create', 'Testing123'])

        # move into the new project directory and install
        os.chdir('Testing123')
        subprocess.check_call([
            py_exe,
            'setup.py',
            'develop'
        ])

    def install_dependency(self, name):
        pip_exe = os.path.join(self.install_dir, 'bin', 'pip')
        proc = subprocess.Popen([
            pip_exe,
            'install',
            '-U',
            name
        ])
        proc.wait()

        return os.path.join(
            self.install_dir,
            'bin',
            name
        )

    def poll(self, proc):
        limit = 30
        for i in range(limit):
            proc.poll()

            # Make sure it's running
            if proc.returncode is None:
                break
            elif i == limit:  # pragma: no cover
                raise RuntimeError("Server process didn't start.")
            time.sleep(.1)

    @unittest.skipUnless(has_internet(), 'Internet connectivity unavailable.')
    @unittest.skipUnless(
        getattr(pecan, '__run_all_tests__', False) is True,
        'Skipping (slow).  To run, `$ python setup.py test --functional.`'
    )
    def test_project_pecan_serve_command(self):
        pecan_exe = os.path.join(self.install_dir, 'bin', 'pecan')

        # Start the server
        proc = subprocess.Popen([
            pecan_exe,
            'serve',
            'config.py'
        ])

        try:
            self.poll(proc)
            retries = 30
            while True:
                retries -= 1
                if retries < 0:  # pragma: nocover
                    raise RuntimeError(
                        "The HTTP server has not replied within 3 seconds."
                    )
                try:
                    # ...and that it's serving (valid) content...
                    resp = urllib2.urlopen('http://localhost:8080/')
                    assert resp.getcode() == 200
                    assert 'This is a sample Pecan project.' in resp.read()
                except urllib2.URLError:
                    pass
                else:
                    break
                time.sleep(.1)
        finally:
            proc.terminate()

    @unittest.skipUnless(has_internet(), 'Internet connectivity unavailable.')
    @unittest.skipUnless(
        getattr(pecan, '__run_all_tests__', False) is True,
        'Skipping (slow).  To run, `$ python setup.py test --functional.`'
    )
    def test_project_pecan_shell_command(self):
        pecan_exe = os.path.join(self.install_dir, 'bin', 'pecan')

        # Start the server
        proc = subprocess.Popen([
            pecan_exe,
            'shell',
            'config.py'
        ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )

        self.poll(proc)

        out, _ = proc.communicate(
            '{"model" : model, "conf" : conf, "app" : app}'
        )
        assert 'testing123.model' in out
        assert 'Config(' in out
        assert 'webtest.app.TestApp' in out

        try:
            # just in case stdin doesn't close
            proc.terminate()
        except:
            pass

    @unittest.skipUnless(has_internet(), 'Internet connectivity unavailable.')
    @unittest.skipUnless(
        getattr(pecan, '__run_all_tests__', False) is True,
        'Skipping (slow).  To run, `$ python setup.py test --functional.`'
    )
    def test_project_tests_command(self):
        py_exe = os.path.join(self.install_dir, 'bin', 'python')

        # Run the tests
        proc = subprocess.Popen([
            py_exe,
            'setup.py',
            'test'
        ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        proc.wait()

        assert proc.stderr.read().splitlines()[-1].strip() == 'OK'

    @unittest.skipUnless(has_internet(), 'Internet connectivity unavailable.')
    @unittest.skipUnless(
        getattr(pecan, '__run_all_tests__', False) is True,
        'Skipping (slow).  To run, `$ python setup.py test --functional.`'
    )
    def test_project_passes_pep8(self):
        # Install pep8
        pep8_exe = self.install_dependency('pep8')

        # Run pep8 on setup.py and the project
        proc = subprocess.Popen([
            pep8_exe,
            'setup.py',
            'testing123'
        ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        proc.wait()

        # No output == good
        output = proc.stdout.read()
        assert output == ''


class TestGunicornServeCommand(TestTemplateBuilds):

    def create_virtualenv(self):
        super(TestGunicornServeCommand, self).create_virtualenv()

        # Install gunicorn
        self.install_dependency('gunicorn')

    @property
    def gunicorn_exe(self):
        return os.path.join(
            self.install_dir,
            'bin',
            'gunicorn_pecan'
        )

    def poll_gunicorn(self, proc, port):
        try:
            self.poll(proc)
            retries = 30
            while True:
                retries -= 1
                if retries < 0:  # pragma: nocover
                    raise RuntimeError(
                        "The gunicorn server has not replied within 3 seconds."
                    )
                try:
                    # ...and that it's serving (valid) content...
                    resp = urllib2.urlopen('http://localhost:%d/' % port)
                    assert resp.getcode() == 200
                    assert 'This is a sample Pecan project.' in resp.read()
                except urllib2.URLError:
                    pass
                else:
                    break
                time.sleep(.1)
        finally:
            proc.terminate()

    @unittest.skipUnless(has_internet(), 'Internet connectivity unavailable.')
    @unittest.skipUnless(
        getattr(pecan, '__run_all_tests__', False) is True,
        'Skipping (slow).  To run, `$ python setup.py test --functional.`'
    )
    def test_serve_from_config(self):
        # Start the server
        proc = subprocess.Popen([
            self.gunicorn_exe,
            'config.py'
        ])

        self.poll_gunicorn(proc, 8080)

    @unittest.skipUnless(has_internet(), 'Internet connectivity unavailable.')
    @unittest.skipUnless(
        getattr(pecan, '__run_all_tests__', False) is True,
        'Skipping (slow).  To run, `$ python setup.py test --functional.`'
    )
    def test_serve_with_custom_bind(self):
        # Start the server
        proc = subprocess.Popen([
            self.gunicorn_exe,
            '--bind=0.0.0.0:9191',
            'config.py'
        ])

        self.poll_gunicorn(proc, 9191)
