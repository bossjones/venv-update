from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import pytest

from testing import cached_wheels
from testing import install_coverage
from testing import pip_freeze
from testing import requirements
from testing import run
from testing import strip_pip_warnings
from testing import TOP
from testing import uncolor
from venv_update import __version__


def it_shows_help_for_prune():
    out, err = run('pip-faster', 'install', '--help')
    assert '''
  --prune                     Uninstall any non-required packages.
  --no-prune                  Do not uninstall any non-required packages.

Package Index Options (including deprecated options):
''' in out  # noqa
    assert err == ''


@pytest.mark.usefixtures('pypi_server')
def it_installs_stuff(tmpdir):
    venv = tmpdir.join('venv')
    install_coverage(venv)

    assert pip_freeze(str(venv)) == '''\
appdirs==1.4.3
coverage==4.4.1
coverage-enable-subprocess==1.0
packaging==16.8
pip==9.0.1
pyparsing==2.2.0
setuptools==35.0.2
six==1.10.0
wheel==0.29.0
'''

    pip = venv.join('bin/pip').strpath
    run(pip, 'install', 'venv-update==' + __version__)

    assert [
        req.split('==')[0]
        for req in pip_freeze(str(venv)).split()
    ] == [
        'appdirs',
        'coverage',
        'coverage-enable-subprocess',
        'packaging',
        'pip',
        'pyparsing',
        'setuptools',
        'six',
        'venv-update',
        'wheel',
    ]

    run(str(venv.join('bin/pip-faster')), 'install', 'pure_python_package')

    assert 'pure-python-package==0.2.1' in pip_freeze(str(venv)).split('\n')


@pytest.mark.usefixtures('pypi_server')
def it_installs_stuff_from_requirements_file(tmpdir):
    venv = tmpdir.join('venv')
    install_coverage(venv)

    pip = venv.join('bin/pip').strpath
    run(pip, 'install', 'venv-update==' + __version__)

    # An arbitrary small package: pure_python_package
    requirements('pure_python_package\nproject_with_c')

    run(str(venv.join('bin/pip-faster')), 'install', '-r', 'requirements.txt')

    frozen_requirements = pip_freeze(str(venv)).split('\n')

    assert 'pure-python-package==0.2.1' in frozen_requirements
    assert 'project-with-c==0.1.0' in frozen_requirements


@pytest.mark.usefixtures('pypi_server')
def it_installs_stuff_with_dash_e_without_wheeling(tmpdir):
    venv = tmpdir.join('venv')
    install_coverage(venv)

    pip = venv.join('bin/pip').strpath
    run(pip, 'install', 'venv-update==' + __version__)

    # Install a package from git with no extra dependencies in editable mode.
    #
    # We need to install a package from VCS instead of the filesystem because
    # otherwise we aren't testing that editable requirements aren't wheeled
    # (and instead might just be testing that local paths aren't wheeled).
    requirements('-e git+git://github.com/Yelp/dumb-init.git@87545be699a13d0fd31f67199b7782ebd446437e#egg=dumb-init')  # noqa

    run(str(venv.join('bin/pip-faster')), 'install', '-r', 'requirements.txt')

    frozen_requirements = pip_freeze(str(venv)).split('\n')
    assert set(frozen_requirements) == set([
        '-e git://github.com/Yelp/dumb-init.git@87545be699a13d0fd31f67199b7782ebd446437e#egg=dumb_init',  # noqa
        'appdirs==1.4.3',
        'coverage-enable-subprocess==1.0',
        'coverage==4.4.1',
        'packaging==16.8',
        'pip==9.0.1',
        'pyparsing==2.2.0',
        'setuptools==35.0.2',
        'six==1.10.0',
        'venv-update==' + __version__,
        'wheel==0.29.0',
        '',
    ])

    # we shouldn't wheel things installed editable
    assert not tuple(cached_wheels(tmpdir))


@pytest.mark.usefixtures('pypi_server')
def it_caches_downloaded_wheels_from_pypi(tmpdir):
    venv = tmpdir.join('venv')
    install_coverage()

    pip = venv.join('bin/pip').strpath
    run(pip, 'install', 'venv-update==' + __version__)

    run(
        venv.join('bin/pip-faster').strpath, 'install',
        # One of the few wheeled things on our pypi
        'wheeled-package',
    )

    assert set(wheel.name for wheel in cached_wheels(tmpdir)) == set((
        'wheeled-package',
    ))


@pytest.mark.usefixtures('pypi_server')
def it_doesnt_wheel_local_dirs(tmpdir):
    venv = tmpdir.join('venv')
    install_coverage(venv)

    pip = venv.join('bin/pip').strpath
    run(pip, 'install', 'venv-update==' + __version__)

    run(
        venv.join('bin/pip-faster').strpath,
        'install',
        TOP.join('tests/testing/packages/dependant_package').strpath,
    )

    frozen_requirements = pip_freeze(str(venv)).split('\n')
    assert set(frozen_requirements) == set([
        'appdirs==1.4.3',
        'coverage==4.4.1',
        'coverage-enable-subprocess==1.0',
        'dependant-package==1',
        'implicit-dependency==1',
        'many-versions-package==3',
        'packaging==16.8',
        'pip==9.0.1',
        'pure-python-package==0.2.1',
        'pyparsing==2.2.0',
        'setuptools==35.0.2',
        'six==1.10.0',
        'venv-update==' + __version__,
        'wheel==0.29.0',
        '',
    ])

    assert set(wheel.name for wheel in cached_wheels(tmpdir)) == set((
        'implicit-dependency',
        'many-versions-package',
        'pure-python-package',
    ))


@pytest.mark.usefixtures('pypi_server')
def it_doesnt_wheel_git_repos(tmpdir):
    venv = tmpdir.join('venv')
    install_coverage(venv)

    pip = venv.join('bin/pip').strpath
    run(pip, 'install', 'venv-update==' + __version__)

    run(
        venv.join('bin/pip-faster').strpath,
        'install',
        'git+git://github.com/Yelp/dumb-init.git@87545be699a13d0fd31f67199b7782ebd446437e#egg=dumb-init',  # noqa
    )

    frozen_requirements = pip_freeze(str(venv)).split('\n')
    assert set(frozen_requirements) == set([
        'appdirs==1.4.3',
        'coverage-enable-subprocess==1.0',
        'coverage==4.4.1',
        'dumb-init==0.5.0',
        'packaging==16.8',
        'pip==9.0.1',
        'pyparsing==2.2.0',
        'setuptools==35.0.2',
        'six==1.10.0',
        'venv-update==' + __version__,
        'wheel==0.29.0',
        '',
    ])

    assert not tuple(cached_wheels(tmpdir))


@pytest.mark.usefixtures('pypi_server')
def it_can_handle_requirements_already_met(tmpdir):
    venv = tmpdir.join('venv')
    install_coverage(venv)

    pip = venv.join('bin/pip').strpath
    run(pip, 'install', 'venv-update==' + __version__)

    requirements('many-versions-package==1')

    run(str(venv.join('bin/pip-faster')), 'install', '-r', 'requirements.txt')
    assert 'many-versions-package==1\n' in pip_freeze(str(venv))

    run(str(venv.join('bin/pip-faster')), 'install', '-r', 'requirements.txt')
    assert 'many-versions-package==1\n' in pip_freeze(str(venv))


@pytest.mark.usefixtures('pypi_server')
def it_gives_proper_error_without_requirements(tmpdir):
    venv = tmpdir.join('venv')
    install_coverage(venv)

    pip = venv.join('bin/pip').strpath
    run(pip, 'install', 'venv-update==' + __version__)

    _, err = run(str(venv.join('bin/pip-faster')), 'install')
    err = strip_pip_warnings(err)
    assert err.startswith('You must give at least one requirement to install')


@pytest.mark.usefixtures('pypi_server')
def it_can_handle_a_bad_findlink(tmpdir):
    venv = tmpdir.join('venv')
    install_coverage(venv)

    pip = venv.join('bin/pip').strpath
    run(pip, 'install', 'venv-update==' + __version__)

    out, err = run(
        str(venv.join('bin/pip-faster')),
        'install', '-vvv',
        '--find-links', 'git+wat://not/a/thing',
        'pure-python-package',
    )
    out = uncolor(out)
    err = strip_pip_warnings(err)

    expected = '''\
Successfully built pure-python-package
Installing collected packages: pure-python-package
'''
    assert expected in out
    # Between this there's:
    # 'changing mode of .../venv/bin/pure-python-script to 775'
    # but that depends on umask
    _, rest = out.split(expected)
    expected2 = '''\
Successfully installed pure-python-package-0.2.1
Cleaning up...
'''
    assert expected2 in rest
    assert err == (
        "  Url 'git+wat://not/a/thing' is ignored. "
        'It is either a non-existing path or lacks a specific scheme.\n'
    )
    assert 'pure-python-package==0.2.1' in pip_freeze(str(venv)).split('\n')


@pytest.mark.usefixtures('pypi_server')
def test_no_conflicts_when_no_deps_specified(tmpdir):
    venv = tmpdir.join('venv')
    install_coverage(venv)

    pip = venv.join('bin/pip').strpath
    run(pip, 'install', 'venv-update==' + __version__)

    pkgdir = tmpdir.join('pkgdir').ensure_dir()
    setup_py = pkgdir.join('setup.py')

    def _setup_py(many_versions_package_version):
        setup_py.write(
            'from setuptools import setup\n'
            'setup(\n'
            '    name="pkg",\n'
            '    install_requires=["many-versions-package=={0}"],\n'
            ')\n'.format(many_versions_package_version)
        )

    cmd = (
        venv.join('bin/pip-faster').strpath, 'install', '--upgrade',
        pkgdir.strpath,
    )

    _setup_py('1')
    run(*cmd)

    _setup_py('2')
    # Should not complain about conflicts since we specified `--no-deps`
    run(*cmd + ('--no-deps',))
