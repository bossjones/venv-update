from __future__ import print_function
from __future__ import unicode_literals
from py._path.local import LocalPath as Path
import pytest

from testing import (
    requirements,
    run,
    strip_coverage_warnings,
    venv_update,
    venv_update_symlink_pwd,
    TOP,
)

from sys import version_info
PY33 = (version_info >= (3, 3))


def test_trivial(tmpdir):
    tmpdir.chdir()
    requirements('')
    venv_update()


def enable_coverage(tmpdir):
    venv = tmpdir.join('virtualenv_run')
    if not venv.isdir():
        run('virtualenv', venv.strpath)
    run(
        venv.join('bin/python').strpath,
        '-m', 'pip.__main__',
        'install',
        '-r', TOP.join('requirements.d/coverage.txt').strpath,
    )


def install_twice(tmpdir, capfd, between):
    """install twice, and the second one should be faster, due to whl caching"""
    tmpdir.chdir()

    # Arbitrary packages that takes a bit of time to install:
    # Should I make a fixture c-extention to remove these dependencies?
    requirements('''\
pudb==2014.1
urwid==1.3.0
simplejson==3.6.5
pyyaml==3.11
pylint==1.4.0
pytest==2.6.4
chroniker
''')

    from time import time
    enable_coverage(tmpdir)
    assert pip_freeze(capfd) == '\n'.join((
        'cov-core==1.15.0',
        'coverage==4.0a1',
        ''
    ))

    start = time()
    venv_update()
    time1 = time() - start
    assert pip_freeze(capfd) == '\n'.join((
        'PyYAML==3.11',
        'Pygments==2.0.1',
        'argparse==1.2.1',
        'astroid==1.3.2',
        'chroniker==0.0.0',
        'logilab-common==0.63.2',
        'pudb==2014.1',
        'py==1.4.26',
        'pylint==1.4.0',
        'pytest==2.6.4',
        'simplejson==3.6.5',
        'six==1.8.0',
        'urwid==1.3.0',
        'wheel==0.24.0',
        ''
    ))

    between()

    enable_coverage(tmpdir)
    # there may be more or less packages depending on what exactly happened between
    assert 'cov-core==1.15.0\ncoverage==4.0a1\n' in pip_freeze(capfd)

    start = time()
    # second install should also need no network access
    # these are arbitrary invalid IP's
    venv_update(
        http_proxy='http://300.10.20.30:40',
        https_proxy='http://400.11.22.33:44',
        ftp_proxy='http://500.4.3.2:1',
    )
    time2 = time() - start
    assert pip_freeze(capfd) == '\n'.join((
        'PyYAML==3.11',
        'Pygments==2.0.1',
        'argparse==1.2.1',
        'astroid==1.3.2',
        'chroniker==0.0.0',
        'logilab-common==0.63.2',
        'pudb==2014.1',
        'py==1.4.26',
        'pylint==1.4.0',
        'pytest==2.6.4',
        'simplejson==3.6.5',
        'six==1.8.0',
        'urwid==1.3.0',
        'wheel==0.24.0',
        ''
    ))

    # second install should be at least twice as fast
    ratio = time1 / time2
    print('%.2fx speedup' % ratio)
    return ratio


@pytest.mark.flaky(reruns=5)
def test_noop_install_faster(tmpdir, capfd):
    def do_nothing():
        pass

    # constrain both ends, to show that we know what's going on
    # 2014-12-10: osx, py27: 4.3, 4.6, 5.0, 5.3
    # 2014-12-10: osx, py34: 8-9
    # 2014-12-10: travis, py34: 11-12
    assert 4 < install_twice(tmpdir, capfd, between=do_nothing) < 13


@pytest.mark.flaky(reruns=5)
def test_cached_clean_install_faster(tmpdir, capfd):
    def clean():
        venv = tmpdir.join('virtualenv_run')
        assert venv.isdir()
        venv.remove()
        assert not venv.exists()

    # I get ~4x locally, but only 2.5x on travis
    # constrain both ends, to show that we know what's going on
    # 2014-12-10: osx, py34: 4.4, 4.6
    # 2014-12-10: travis, py34: 6.5-7.0
    # 2014-12-16: travis, py27: 2.8-3.7
    assert 2.75 < install_twice(tmpdir, capfd, between=clean) < 7


def test_arguments_version(tmpdir, capfd):
    """Show that we can pass arguments through to virtualenv"""
    tmpdir.chdir()

    from subprocess import CalledProcessError
    with pytest.raises(CalledProcessError) as excinfo:
        # should show virtualenv version, then crash
        venv_update('--version')

    assert excinfo.value.returncode == 1
    out, err = capfd.readouterr()
    lasterr = strip_coverage_warnings(err).rsplit('\n', 2)[-2]
    assert lasterr.startswith('virtualenv executable not found: /'), err
    assert lasterr.endswith('/virtualenv_run/bin/python'), err

    lines = out.split('\n')
    assert len(lines) == 3, lines
    assert lines[0] == ('> virtualenv virtualenv_run --version'), lines


def test_arguments_system_packages(tmpdir, capfd):
    """Show that we can pass arguments through to virtualenv"""
    tmpdir.chdir()
    requirements('')

    venv_update('--system-site-packages', 'virtualenv_run', 'requirements.txt')
    out, err = capfd.readouterr()  # flush buffers

    run('virtualenv_run/bin/python', '-c', '''\
import sys
for p in sys.path:
    if p.startswith(sys.real_prefix) and p.endswith("-packages"):
        print(p)
        break
''')
    out, err = capfd.readouterr()
    assert strip_coverage_warnings(err) == ''
    out = out.rstrip('\n')
    assert out and Path(out).isdir()


def pip(*args):
    # because the scripts are made relative, it won't use the venv python without being explicit.
    run('virtualenv_run/bin/python', 'virtualenv_run/bin/pip', *args)


def pip_freeze(capfd):
    out, err = capfd.readouterr()  # flush any previous output

    pip('freeze', '--local')
    out, err = capfd.readouterr()

    assert strip_coverage_warnings(err) == ''
    return out


def test_update_while_active(tmpdir, capfd):
    tmpdir.chdir()
    requirements('')

    venv_update()
    assert 'mccabe' not in pip_freeze(capfd)

    # An arbitrary small package: mccabe
    requirements('mccabe')

    venv_update_symlink_pwd()
    run('sh', '-c', '. virtualenv_run/bin/activate && python venv_update.py')
    assert 'mccabe' in pip_freeze(capfd)


def test_scripts_left_behind(tmpdir):
    tmpdir.chdir()
    requirements('')

    venv_update()

    # an arbitrary small package with a script: pep8
    script_path = Path('virtualenv_run/bin/pep8')
    assert not script_path.exists()

    pip('install', 'pep8')
    assert script_path.exists()

    venv_update()
    assert not script_path.exists()


def assert_timestamps(*reqs):
    firstreq = Path(reqs[0])
    lastreq = Path(reqs[-1])

    venv_update('virtualenv_run', *reqs)

    assert firstreq.mtime() < Path('virtualenv_run').mtime()

    # garbage, to cause a failure
    lastreq.write('-w wat')

    from subprocess import CalledProcessError
    with pytest.raises(CalledProcessError) as excinfo:
        venv_update('virtualenv_run', *reqs)

    assert excinfo.value.returncode == 1
    assert firstreq.mtime() > Path('virtualenv_run').mtime()

    # blank requirements should succeed
    lastreq.write('')

    venv_update('virtualenv_run', *reqs)
    assert Path(reqs[0]).mtime() < Path('virtualenv_run').mtime()


def test_timestamps_single(tmpdir):
    tmpdir.chdir()
    requirements('')
    assert_timestamps('requirements.txt')


def test_timestamps_multiple(tmpdir):
    tmpdir.chdir()
    requirements('')
    Path('requirements2.txt').write('')
    assert_timestamps('requirements.txt', 'requirements2.txt')


def readall(fd):
    """My own read loop, bc the one in python3.4 is derpy atm:
    http://bugs.python.org/issue21090#msg231093
    """
    from os import read
    result = []
    lastread = None
    while lastread != b'':
        try:
            lastread = read(fd, 4 * 1024)
        except OSError as error:
            if error.errno == 5:  # pty end-of-file  -.-
                break
            else:
                raise
        result.append(lastread)
    return b''.join(result).decode('US-ASCII')


def pipe_output(read, write):
    from os import environ
    environ = environ.copy()
    environ['HOME'] = str(Path('.').realpath())

    from subprocess import Popen
    vupdate = Popen(
        ('venv-update', '--version'),
        env=environ,
        stdout=write,
        close_fds=True,
    )

    from os import close
    close(write)
    result = readall(read)
    close(read)
    vupdate.wait()
    return result


def unprintable(mystring):
    """return only the unprintable characters of a string"""
    # TODO: unit-test
    from string import printable
    return ''.join(
        character
        for character in mystring
        if character not in printable
    )


def test_colored_tty():
    from os import openpty
    read, write = openpty()

    out = pipe_output(read, write)

    assert unprintable(out), out


def test_uncolored_pipe():
    from os import pipe
    read, write = pipe()

    out = pipe_output(read, write)

    assert not unprintable(out), out
