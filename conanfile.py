#!/usr/bin/env python
# -*- coding: future_fstrings -*-
# -*- coding: utf-8 -*-

import os, re
from conans import ConanFile, CMake, tools


class CeresSolverConan(ConanFile):
    """ Tested with versions: 1.9.0, 1.11.0, 1.13.0 """

    name            = 'ceres_solver'
    license         = 'http://ceres-solver.org/license.html'
    url             = 'http://ceres-solver.org/'
    description     = 'A large scale non-linear optimization library'
    settings        = 'os', 'compiler', 'build_type', 'arch'
    options         = {'shared': [True, False]}
    default_options = 'shared=True'
    exports         = "patch*"
    build_policy    = 'missing'
    generators      = 'cmake'
    requires = (
        'glog/[>0.3.1]@ntc/stable'
    )

    def requirements(self):
        version_major = int(self.version.split('.')[1])
        if version_major < 13:
            self.requires('eigen/[>=3.2.0,<3.3.4]@ntc/stable')
        else:
            self.requires('eigen/[>=3.2.0]@ntc/stable')

    def configure(self):
        self.options["glog"].shared = self.options.shared

    def source(self):
        self.run(f'git clone https://ceres-solver.googlesource.com/ceres-solver {self.name}')
        self.run(f'cd {self.name} && git checkout {self.version}')

        patch_file = f'patch-{self.version}'
        if os.path.exists(patch_file):
            tools.patch(patch_file=patch_file, base_path=self.name)

    def build(self):

        args = []
        args.append('-DCMAKE_CXX_FLAGS="-mtune=generic"')
        args.append('-DBUILD_SHARED_LIBS=%s'%('TRUE' if self.options.shared else 'FALSE'))
        args.append('-DCXX11:BOOL=On')
        args.append('-DNO_CMAKE_PACKAGE_REGISTRY:BOOL=On')
        args.append('-DEIGEN_INCLUDE_DIR:PATH=%s'%os.path.join(self.deps_cpp_info['eigen'].rootpath, 'include', 'eigen3'))
        args.append('-DEigen3_DIR:PATH=%s'%os.path.join(self.deps_cpp_info['eigen'].rootpath, 'share', 'eigen3', 'cmake'))

        args.append('-Dglog_DIR:PATH=%s'%self.deps_cpp_info['glog'].rootpath)
        args.append('-DGLOG_INCLUDE_DIR:PATH=%s'%os.path.join(self.deps_cpp_info['glog'].rootpath, 'include'))
        args.append('-DGLOG_LIBRARY:PATH=%s'%';'.join(os.path.join(self.deps_cpp_info['glog'].rootpath, self.deps_cpp_info['glog'].libdirs[0], l) for l in self.deps_cpp_info['glog'].libs))
        def guessGlogLib():
            name = 'glog'
            if 'Windows' == self.settings.os:
                prefix = ''
                suffix = 'lib'
            else:
                prefix = 'lib'
                suffix = 'so' if self.options['glog'].shared else 'a'
            return os.path.join(self.deps_cpp_info['glog'].rootpath, self.deps_cpp_info['glog'].libdirs[0], f'{prefix}{name}.{suffix}')

        # If not specifies, ceres will find the system version
        args.append('-DGLOG_LIBRARY:PATH=%s'%guessGlogLib())

        args.append('-Wno-dev')

        self.output.info('CMake flags:\n%s'%'\n'.join(args))

        cmake = CMake(self)
        cmake.configure(source_folder=self.name, args=args)
        cmake.build()
        cmake.install()

        # Every version of Ceres seems to install this file into a different location
        for p in [os.path.join('share', 'Ceres'), 'CMake', os.path.join('lib', 'cmake', 'Ceres')]:
            path = os.path.join(self.package_folder, p, 'CeresConfig.cmake')
            if os.path.exists(path):
                self.fixFindPackage(path)

    def fixFindPackage(self, path):
        """ Remove absolute paths from the CMake file """

        if not os.path.exists(path):
            self.output.warn(f'Cannot find CMake find script for Ceres-Solver: {path}')
            return

        with open(path) as f: data = f.read()

        regex = r'Eigen[^\s]+ (?P<base>.*.data.eigen.(?P<version>\d+.\d+.\d+).*?[a-z0-9]{40})'
        m = re.search(regex, data, re.IGNORECASE)
        if m:
            data = data.replace(m.group('base'), '${CONAN_EIGEN_ROOT}')
            data = data.replace(m.group('version'), self.deps_cpp_info['eigen'].version)
        else:
            self.output.warn(f'Cannot find absolute path to Eigen in CMake find script for Ceres-Solver: {path}')

        regex = r'glog_DIR\s+(?P<base>.*?glog.*?[a-z0-9]{40})'
        m = re.search(regex, data, re.IGNORECASE)
        if m:
            data = data.replace(m.group('base'), '${CONAN_GLOG_ROOT}')
        else:
            self.output.warn(f'Cannot find absolute path to Glog in CMake find script for Ceres-Solver: {path}')

        regex = r'GLOG[\w_]+DIR\s+(?P<base>.*?glog.*?[a-z0-9]{40})'
        m = re.search(regex, data, re.IGNORECASE)
        if m:
            data = data.replace(m.group('base'), '${CONAN_GLOG_ROOT}')
        else:
            self.output.warn(f'Cannot find absolute path to Glog in CMake find script for Ceres-Solver: {path}')

        with open(path, 'w') as f: f.write(data)

    def package(self):
        pass

    def package_info(self):
        # The CMake files move in different versions, so we're going to use the
        # resdir to point to these.
        version_major = int(self.version.split('.')[1])
        if version_major >= 13:
            self.cpp_info.resdirs.append('/'.join(['lib', 'cmake', 'Ceres']))
        elif version_major == 11:
            self.cpp_info.resdirs.append('/'.join(['share', 'Ceres']))
        elif version_major == 9:
            self.cpp_info.resdirs.append('CMake')
        else:
            self.output.warn('Not sure where to place CMake Find Script')

        if self.settings.os == 'Linux':
            lib = 'libceres.%s'%('so' if self.options.shared else 'a')
        else:
            lib = 'ceres.lib'

        self.cpp_info.libs.append(lib)


# vim: ts=4 sw=4 expandtab ffs=unix ft=python foldmethod=marker :
