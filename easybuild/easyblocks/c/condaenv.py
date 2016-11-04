##
# Copyright 2009-2016 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##
"""
EasyBuild support for building and installing conda environments via conda env
create -p, implemented as an easyblock @author: Jillian Rowe (New York
University Abu Dhabi)
"""

import os
import shutil
import stat

import easybuild.tools.environment as env
from easybuild.framework.easyblock import EasyBlock
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.filetools import rmtree2
from easybuild.tools.run import run_cmd
from easybuild.easyblocks.anaconda import initialize_conda_env, set_conda_env

class EB_CondaEnv(EasyBlock):
    """Support for building/installing environments using conda env. You must use conda-env >= 2.5.2"""

    @staticmethod
    def extra_options(extra_vars=None):
        """Extra easyconfig parameters specific to EB_CondaEnv easyblock."""
        extra_vars = EasyBlock.extra_options(extra_vars)
        extra_vars.update({
            'environment_file': [None, "Environment.yml file. Either add a 'environment.yml' to your sources, or specify the full path here.", CUSTOM],
            'post_install_cmd': [None, "Commands after install: pip install, cpanm install, etc", CUSTOM],
            'pre_install_cmd': [None, "Commands before install: setting environment variables, etc", CUSTOM],
            'remote_environment': [None, "Remote definition file", CUSTOM],
        })
        return extra_vars

    def __init__(self, *args, **kwargs):
        """Initialize EB_CondaEnv-specific variables."""
        super(EB_CondaEnv, self).__init__(*args, **kwargs)

    def extract_step(self):
        """Move all source files to the build directory"""

        if not self.src:
            pass
        else:
            self.src[0]['finalpath'] = self.builddir

            # copy source to build dir.
            for source in self.src:
                src = source['path']
                dst = os.path.join(self.builddir, source['name'])
                try:
                    shutil.copy2(src, self.builddir)
                    os.chmod(dst, stat.S_IRWXU)
                except (OSError, IOError), err:
                    raise EasyBuildError("Couldn't copy %s to %s: %s", src, self.builddir, err)

    def configure_step(self):
        """No configuration, this is binary software"""
        pass

    def build_step(self):
        """No compilation, this is binary software"""
        pass

    def install_step(self):
        """Copy all files in build directory to the install directory"""

        if self.cfg['pre_install_cmd']:
            run_cmd(self.cfg['pre_install_cmd'], log_all=True, simple=True)

        initialize_conda_env(self.installdir)

        set_conda_env(self.installdir)

        if self.cfg['environment_file']:
            cmd = "conda env create  -f {} -p {}".format(self.cfg['environment_file'], self.installdir)
        elif self.cfg['remote_environment']:
            cmd = "conda env create  {} -p {}".format(self.cfg['remote_environment'], self.installdir)
        else:
            cmd = "conda env create  -p {}".format(self.installdir)

        run_cmd(cmd, log_all=True, simple=True)

        self.log.info('Installed conda env')

        if self.cfg['post_install_cmd']:
            run_cmd(self.cfg['post_install_cmd'], log_all=True, simple=True)

    def make_module_extra(self):
        """Add the install directory to the PATH."""

        txt = super(EB_CondaEnv, self).make_module_extra()
        txt += self.module_generator.set_environment('CONDA_ENV', self.installdir)
        txt += self.module_generator.set_environment('CONDA_DEFAULT_ENV', self.installdir)
        self.log.debug("make_module_extra added this: %s" % txt)
        return txt

    def make_module_req_guess(self):
        """
        A dictionary of possible directories to look for.
        """
        return {
            'PATH': ['bin', 'sbin'],
            'MANPATH': ['man', os.path.join('share', 'man')],
            'PKG_CONFIG_PATH': [os.path.join(x, 'pkgconfig') for x in ['lib', 'lib32', 'lib64', 'share']],
        }
