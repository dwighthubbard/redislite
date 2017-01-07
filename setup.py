#!/usr/bin/env python
# Copyright (c) 2015, Yahoo Inc.
# Copyrights licensed under the New BSD License
# See the accompanying LICENSE.txt file for terms.
from __future__ import print_function
import os
import json
import logging
from setuptools import setup
from setuptools.command.install import install
from distutils.command.build import build
from distutils.core import Extension
import distutils.util
import sys
from subprocess import call

logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger('setup')
UNSUPPORTED_PLATFORMS = ['win32', 'win64']
UNSUPPORTED_PLATFORMS = []
WINDOWS_REDIS_SERVER = '/Program Files/Redis/redis-server.exe'
METADATA_FILENAME = 'redislite/package_metadata.json'
BASEPATH = os.path.dirname(os.path.abspath(__file__))
REDIS_PATH = os.path.join(BASEPATH, 'redis.submodule')
REDIS_SERVER_METADATA = {}
install_scripts = ''


def readme():
    with open('README.rst') as f:
        return f.read()


class BuildRedis(build):
    global REDIS_SERVER_METADATA

    def run(self):
        # run original build code
        build.run(self)

        # build Redis
        LOG.debug('Running build_redis')

        os.environ['CC'] = 'gcc'
        os.environ['PREFIX'] = REDIS_PATH
        cmd = [
            'make',
            'MALLOC=libc',
            'V=' + str(self.verbose),
        ]

        targets = ['install']
        cmd.extend(targets)

        target_files = [
            os.path.join(REDIS_PATH, 'bin/redis-server'),
            os.path.join(REDIS_PATH, 'bin/redis-cli'),
        ]

        def _compile():
            LOG.debug('Running compile in %r', os.getcwd())
            call(cmd, cwd=REDIS_PATH)

        self.execute(_compile, [], 'compiling redis')

        # copy resulting tool to script folder
        self.mkpath(self.build_scripts)

        if not self.dry_run:
            for target in target_files:
                LOG.debug('copy: %s -> %s', target, self.build_scripts)
                self.copy_file(target, self.build_scripts)


def add_redis_metadata(server_filename, metadata_filename):
    """
    Add the redis server metadata to the metadata file

    Parameters
    ----------
    server_filename : str
        The filename of the redis server

    metadata_filename : str
        The filename of the metadata file
    """
    global REDIS_SERVER_METADATA
    if not os.path.exists(server_filename) or not os.path.exists(metadata_filename):
        return

    with open(metadata_filename) as fh:
        metadata = json.load(fh)
        metadata['redis_bin'] = server_filename

    # Store the redis-server --version output for later
    for line in os.popen('"%s" --version' % metadata['redis_bin']).readlines():
        line = line.strip()
        for item in line.split():
            if '=' in item:
                key, value = item.split('=')
                REDIS_SERVER_METADATA[key] = value
    metadata['redis_server'] = REDIS_SERVER_METADATA
    LOG.debug('new metadata: %s', metadata)
    with open(metadata_filename, 'w') as metadata_handle:
        json.dump(metadata, metadata_handle, indent=4)


class InstallRedis(install):
    build_scripts = None

    def initialize_options(self):
        install.initialize_options(self)

    def finalize_options(self):
        install.finalize_options(self)
        self.set_undefined_options('build', ('build_scripts', 'build_scripts'))

    def run(self):
        global install_scripts
        # run original install code
        install.run(self)

        # install Redis executables
        LOG.debug(
            'running InstallRedis %s -> %s', self.build_lib, self.install_lib
        )
        self.copy_tree(self.build_lib, self.install_lib)
        module_bin = os.path.join(self.install_lib, 'redislite/bin')
        if not os.path.exists(module_bin):
            os.makedirs(module_bin, 0o0755)
        self.copy_tree(self.build_scripts, module_bin)
        LOG.debug(
            'running InstallRedis %s -> %s',
            self.build_scripts, self.install_scripts
        )
        self.copy_tree(self.build_scripts, self.install_scripts)

        install_scripts = self.install_scripts
        LOG.debug('install_scripts: %s', install_scripts)
        md_file = os.path.join(
            self.install_lib, 'redislite/package_metadata.json'
        )
        server_filename = os.path.join(module_bin, 'redis-server')
        if not os.path.exists(server_filename):
            server_filename = os.path.join(install_scripts, 'redis-server')
        add_redis_metadata(server_filename=server_filename, metadata_filename=md_file)

# Create a dictionary of our arguments, this way this script can be imported
#  without running setup() to allow external scripts to see the setup settings.
args = {
    'name': 'redislite',
    'version': '3.0.0',
    'author': 'Dwight Hubbard',
    'author_email': 'dhubbard@yahoo-inc.com',
    'url': 'https://github.com/yahoo/redislite',
    'license': 'BSD',
    'keywords': 'Redis sqlite',
    'packages': ['redislite'],
    'description': 'Redis built into a python package',
    'install_requires': ['redis', 'psutil'],
    'requires': ['redis', 'psutil'],
    'long_description': readme(),
    'classifiers': [
            'Development Status :: 4 - Beta',
            'Environment :: Console',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: BSD License',
            'Operating System :: MacOS :: MacOS X',
            'Operating System :: POSIX :: BSD :: FreeBSD',
            'Operating System :: POSIX :: Linux',
            'Operating System :: POSIX :: SunOS/Solaris',
            'Operating System :: POSIX',
            'Programming Language :: C',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: Implementation :: CPython',
            'Programming Language :: Python :: Implementation :: PyPy',
            'Programming Language :: Python',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: Software Development :: Libraries',
            'Topic :: System :: Systems Administration',
            'Topic :: Utilities',
    ],
    'package_data': {
        'redislite': ['package_metadata.json', 'bin/redis-server'],
    },
    'include_package_data': True,
    'cmdclass': {
        'build': BuildRedis,
        'install': InstallRedis,
    },

    # We put in a bogus extension module so wheel knows this package has
    # compiled components.
    'ext_modules': [
        Extension(
            'dummy',
            sources=[
                'src/dummy.c'
            ]
        )
    ],
    # 'extras_require': {
    #     ':sys_platform=="darwin"': [],
    #     ':sys_platform=="linux"': [],
    # }
}
setup_arguments = args

# Add any scripts we want to package
if os.path.isdir('scripts'):
    setup_arguments['scripts'] = [
        os.path.join('scripts', f) for f in os.listdir('scripts')
    ]


class Git(object):
    version_list = ['0', '7', '0']

    def __init__(self, version=None):
        if version:
            self.version_list = version.split('.')

    @property
    def version(self):
        """
        Generate a Unique version value from the git information
        :return:
        """
        git_rev = len(os.popen('git rev-list HEAD').readlines())
        if git_rev != 0:
            self.version_list[-1] = '%d' % git_rev
        version = '.'.join(self.version_list)
        return version

    @property
    def branch(self):
        """
        Get the current git branch
        :return:
        """
        return os.popen('git rev-parse --abbrev-ref HEAD').read().strip()

    @property
    def hash(self):
        """
        Return the git hash for the current build
        :return:
        """
        return os.popen('git rev-parse HEAD').read().strip()

    @property
    def origin(self):
        """
        Return the fetch url for the git origin
        :return:
        """
        for item in os.popen('git remote -v'):
            split_item = item.strip().split()
            if split_item[0] == 'origin' and split_item[-1] == '(push)':
                return split_item[1]


def get_and_update_metadata():
    """
    Get the package metadata or generate it if missing
    :return:
    """
    global METADATA_FILENAME
    global REDIS_SERVER_METADATA

    if not os.path.exists('.git') and os.path.exists(METADATA_FILENAME):
        with open(METADATA_FILENAME) as fh:
            metadata = json.load(fh)
    else:
        git = Git(version=setup_arguments['version'])
        metadata = {
            'git_version': git.version,
            'git_origin': git.origin,
            'git_branch': git.branch,
            'git_hash': git.hash,
            'version': git.version,
            'redis_server': REDIS_SERVER_METADATA,
            'redis_bin': install_scripts
        }
        with open(METADATA_FILENAME, 'w') as fh:
            json.dump(metadata, fh, indent=4)
    return metadata


if __name__ == '__main__':
    if sys.platform in ['win32'] and os.path.exists(WINDOWS_REDIS_SERVER):
        LOG.debug(
            'Using binary redis server at %s' % WINDOWS_REDIS_SERVER
        )
        del args['ext_modules']
        del args['cmdclass']
        add_redis_metadata(server_filename=WINDOWS_REDIS_SERVER, metadata_filename=METADATA_FILENAME)
    else:
        if sys.platform in UNSUPPORTED_PLATFORMS:
            print(
                'The redislite module is not supported on the %r '
                'platform' % sys.platform,
                file=sys.stderr
            )
            sys.exit(1)
        os.environ['CC'] = 'gcc'
        logging.basicConfig(level=logging.DEBUG)
        LOG.debug('Building for platform: %s', distutils.util.get_platform())

    metadata = get_and_update_metadata()
    setup_arguments['version'] = metadata['version']
    setup(**setup_arguments)
