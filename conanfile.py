#!/usr/bin/env python
# -*- coding: future_fstrings -*-
# -*- coding: utf-8 -*-

import os, re
from conans import ConanFile, CMake, tools
from conans.model.version import Version
from conans.errors import ConanException


class CeresSolverConan(ConanFile):
    """ Tested with versions: 1.9.0, 1.11.0, 1.13.0 """

    name            = 'ceres_solver'
    version         = '1.9.0'
    license         = 'http://ceres-solver.org/license.html'
    url             = 'https://github.com/kheaactua/conan-ceres_solver'
    description     = 'A large scale non-linear optimization library'
    settings        = 'os', 'compiler', 'build_type', 'arch', 'arch_build'
    options         = {
        'shared': [True, False],
        'fPIC':   [True, False],
        'cxx11':  [True, False],
        'suitesparse': [True, False],
        'cxsparse':    [True, False],
        'custom_blas': [True, False],
        'openblas':    [True, False],
    }
    default_options = (
        'shared=True',
         'fPIC=True',
         'cxx11=True',
         'suitesparse=True',
         'cxsparse=False',
         'custom_blas=True',
         'openblas=True',
    )
    exports         = "patch*"
    build_policy    = 'missing'
    requires = (
        'glog/[>0.3.1]@ntc/stable',
        'suitesparse/[>4.0]@ntc/stable',
    )


    def build_requirements(self):
        pack_names = None
        if tools.os_info.linux_distro == "ubuntu":
            pack_names = ['build-essential'] # , 'libsuitesparse-dev']

            if self.settings.arch == "x86":
                full_pack_names = []
                for pack_name in pack_names:
                    full_pack_names += [pack_name + ":i386"]
                pack_names = full_pack_names

        if pack_names:
            installer = tools.SystemPackageTool()
            try:
                installer.update() # Update the package database
                installer.install(" ".join(pack_names)) # Install the package
            except ConanException:
                self.output.warn('Could not run system updates for build requirements')

    def requirements(self):
        version_major = int(self.version.split('.')[1])
        if version_major < 13:
            self.requires('eigen/[>=3.2.0,<3.3.4]@ntc/stable')
        else:
            self.requires('eigen/[>=3.2.0]@ntc/stable')

        if 'Linux' == self.settings.os and self.options.openblas:
                self.requires('openblas/0.3.1@ntc/stable')

    def config_options(self):
        if self.settings.compiler == "Visual Studio":
            self.options.remove("fPIC")
            self.options.remove("openblas")

    def configure(self):
        self.options["glog"].shared = self.options.shared

    def source(self):
        self.run(f'git clone https://ceres-solver.googlesource.com/ceres-solver {self.name}')
        self.run(f'cd {self.name} && git checkout {self.version}')

        patch_file = f'patch-{self.version}'
        if os.path.exists(patch_file):
            tools.patch(patch_file=patch_file, base_path=self.name)

    def _set_up_cmake(self):
        """
        Set up the CMake generator so that it can be used in build() and package()
        """

        cmake = CMake(self)

        # Normally we would do this in config_options(), but since it's
        # contigent on the version of eigen which we don't know at that point,
        # we're doing it here.
        if Version(str(self.deps_cpp_info['eigen'].version)) <= '3.2.5':
            self.options.remove("cxx11")

        if 'cxx11' in self.options and self.options.cxx11:
            cmake.definitions['CMAKE_CXX_STANDARD'] = 11

        if 'fPIC' in self.options and self.options.fPIC:
            cmake.definitions['CMAKE_POSITION_INDEPENDENT_CODE'] = 'ON'

        # Not currently used.  Should probably be included by wrapping the CMake file in source()
        # if self.settings.compiler in ['gcc']:
        #     cxx_flags.append('-mtune=generic')
        #     cxx_flags.append('-frecord-gcc-switches')
        # if len(cxx_flags):
        #     cmake.definitions['ADDITIONAL_CXX_FLAGS:STRING'] = ' '.join(cxx_flags)

        cmake.definitions['BUILD_SHARED_LIBS:BOOL'] = 'TRUE' if self.options.shared else 'FALSE'
        cmake.definitions['NO_CMAKE_PACKAGE_REGISTRY:BOOL'] = 'On'
        cmake.definitions['EIGEN_INCLUDE_DIR:PATH'] = os.path.join(self.deps_cpp_info['eigen'].rootpath, 'include', 'eigen3')

        # These two are reported as 'unused', but I think they are used by
        # cmake/Find*.cmake, or if not, they should be (would make the rest
        # simpler)
        cmake.definitions['Glog_DIR:PATH'] = self.deps_cpp_info['glog'].rootpath
        cmake.definitions['Eigen3_DIR:PATH'] = os.path.join(self.deps_cpp_info['eigen'].rootpath, 'share', 'eigen3', 'cmake')

        cmake.definitions['GLOG_INCLUDE_DIR:PATH'] = os.path.join(self.deps_cpp_info['glog'].rootpath, 'include')
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
        cmake.definitions['GLOG_LIBRARY:PATH'] = guessGlogLib()

        if 'Linux' == self.settings.os:
            libext = 'so'
        else:
            libext = 'lib'

        cmake.definitions['CUSTOM_BLAS:BOOL'] = 'ON' if self.options.custom_blas else 'OFF'

        if self.options.suitesparse:
            cmake.definitions['SUITESPARSE:BOOL'] = 'ON'

            suitesparse_inc_base_dir = os.path.join(self.deps_cpp_info['suitesparse'].rootpath, self.deps_cpp_info['suitesparse'].includedirs[0])
            suitesparse_inc_dir      = os.path.join(suitesparse_inc_base_dir, 'suitesparse')

            suitesparse_lib_dir      = os.path.join(self.deps_cpp_info['suitesparse'].rootpath, self.deps_cpp_info['suitesparse'].libdirs[0])

            cmake.definitions['SUITESPARSEQR_INCLUDE_DIR:PATH']      = suitesparse_inc_base_dir
            cmake.definitions['SUITESPARSEQR_LIBRARY:FILEPATH']      = os.path.join(suitesparse_lib_dir, f'libspqr.{libext}')

            cmake.definitions['SUITESPARSE_CONFIG_INCLUDE_DIR:PATH'] = suitesparse_inc_dir
            cmake.definitions['SUITESPARSE_CONFIG_LIBRARY:FILEPATH'] = os.path.join(suitesparse_lib_dir, '%ssuitesparseconfig.%s'%('lib' if 'Linux' == self.settings.os else '', libext))

            cmake.definitions['AMD_INCLUDE_DIR:PATH']                = suitesparse_inc_dir
            cmake.definitions['AMD_LIBRARY:FILEPATH']                = os.path.join(suitesparse_lib_dir, f'libamd.{libext}')

            cmake.definitions['CAMD_INCLUDE_DIR:PATH']               = suitesparse_inc_dir
            cmake.definitions['CAMD_LIBRARY:FILEPATH']               = os.path.join(suitesparse_lib_dir, f'libcamd.{libext}')

            cmake.definitions['SUITESPARSEQR_INCLUDE_DIR:PATH']      = suitesparse_inc_dir
            cmake.definitions['SUITESPARSEQR_LIBRARY:FILEPATH']      = os.path.join(suitesparse_lib_dir, f'libspqr.{libext}')

            cmake.definitions['COLAMD_INCLUDE_DIR:PATH']             = suitesparse_inc_dir
            cmake.definitions['COLAMD_LIBRARY:FILEPATH']             = os.path.join(suitesparse_lib_dir, f'libcolamd.{libext}')

            cmake.definitions['CCOLAMD_INCLUDE_DIR:PATH']            = suitesparse_inc_dir
            cmake.definitions['CCOLAMD_LIBRARY:FILEPATH']            = os.path.join(suitesparse_lib_dir, f'libccolamd.{libext}')

            cmake.definitions['CHOLMOD_INCLUDE_DIR:PATH']            = suitesparse_inc_dir
            cmake.definitions['CHOLMOD_LIBRARY:FILEPATH']            = os.path.join(suitesparse_lib_dir, f'libcholmod.{libext}')

            if 'Windows' == self.settings.os:
                cmake.definitions['SUITESPARSE_INCLUDE_DIR_HINTS:PATH'] = suitesparse_inc_dir
                cmake.definitions['SUITESPARSE_LIBRARY_DIR_HINTS:PATH'] = suitesparse_lib_dir
                if 'openblas' not in self.deps_cpp_info.deps:
                    cmake.definitions['BLAS_blas_LIBRARY:FILEPATH']     = os.path.join(suitesparse_lib_dir, f'libblas.{libext}')
                    cmake.definitions['LAPACK_lapack_LIBRARY:FILEPATH'] = os.path.join(suitesparse_lib_dir, f'liblapack.{libext}')

            if 'openblas' in self.deps_cpp_info.deps:
                libopenblas = os.path.join(self.deps_cpp_info['openblas'].rootpath, self.deps_cpp_info['openblas'].libdirs[0], f'libopenblas.{libext}')
                cmake.definitions['BLAS_openblas_LIBRARY:FILEPATH']   = libopenblas
                cmake.definitions['LAPACK_openblas_LIBRARY:FILEPATH'] = libopenblas

        else:
            cmake.definitions['SUITESPARSE:BOOL'] = 'ON'

        if self.options.cxsparse:
            cmake.definitions['CXSPARSE:BOOL']    = 'ON'
            cmake.definitions['CXSPARSE_INCLUDE_DIR:PATH'] = os.path.join(self.deps_cpp_info['suitesparse'].rootpath, self.deps_cpp_info['suitesparse'].includedirs[0], 'suitesparse')
            cmake.definitions['CXSPARSE_LIBRARY:FILEPATH'] = os.path.join(self.deps_cpp_info['suitesparse'].rootpath, self.deps_cpp_info['suitesparse'].libdirs[0], 'libcxsparse.so')

            if 'Windows' == self.settings.os:
                cmake.definitions['CXSPARSE_INCLUDE_DIR_HINTS:PATH']    = suitesparse_inc_dir
                cmake.definitions['CXSPARSE_LIBRARY_DIR_HINTS:PATH']    = suitesparse_lib_dir

        else:
            cmake.definitions['CXSPARSE:BOOL']    = 'OFF'

        return cmake

    def build(self):
        args = []
        args.append('-Wno-dev')

        cmake = self._set_up_cmake()
        self.output.info('CMake flags:\n%s'%'\n'.join(args))
        s = '\nCMake Definitions:\n'
        for k,v in cmake.definitions.items():
            s += ' - %s=%s\n'%(k, v)
        self.output.info(s)

        cmake.configure(source_folder=self.name, args=args)
        cmake.build()

    def package(self):
        # Use cmake's install target
        cmake = self._set_up_cmake()
        cmake.configure(source_folder=os.path.join(self.build_folder, self.name), build_folder=self.build_folder)
        cmake.install()

        # Every version of Ceres seems to install this file into a different location
        cmake_src_file=os.path.join(self.build_folder, 'CeresConfig.cmake')
        for p in [os.path.join('share', 'Ceres'), 'CMake', os.path.join('lib', 'cmake', 'Ceres')]:
            cmake_dst_file = os.path.join(self.package_folder, p, 'CeresConfig.cmake')
            if os.path.exists(cmake_dst_file):
                self.output.info('Inserting Conan variables in to the Ceres-Solver CMake Find script at found at %s and writting to %s'%(cmake_src_file, cmake_dst_file))
                self.fixFindPackage(
                    src=cmake_src_file,
                    dst=cmake_dst_file
                )

    def fixFindPackage(self, src, dst):
        """ Remove absolute paths from the CMake file """

        if not os.path.exists(src):
            self.output.warn(f'Cannot find CMake find script for Ceres-Solver: {src}')
            return

        with open(src) as f: data = f.read()

        regex = r'Eigen[^\s]+ (?P<base>.*.data.eigen.(?P<version>\d+.\d+.\d+).*?[a-z0-9]{40})'
        m = re.search(regex, data, re.IGNORECASE)
        if m:
            data = data.replace(m.group('base'), '${CONAN_EIGEN_ROOT}')
            data = data.replace(m.group('version'), self.deps_cpp_info['eigen'].version)
        else:
            self.output.warn(f'Cannot find absolute path to Eigen in CMake find script for Ceres-Solver: {src}')

        regex = r'glog_DIR\s+(?P<base>.*?glog.*?[a-z0-9]{40})'
        m = re.search(regex, data, re.IGNORECASE)
        if m:
            data = data.replace(m.group('base'), '${CONAN_GLOG_ROOT}')
        else:
            self.output.warn(f'Cannot find absolute path to Glog in CMake find script for Ceres-Solver: {src}')

        regex = r'GLOG[\w_]+DIR\s+(?P<base>.*?glog.*?[a-z0-9]{40})'
        m = re.search(regex, data, re.IGNORECASE)
        if m:
            data = data.replace(m.group('base'), '${CONAN_GLOG_ROOT}')
        else:
            self.output.warn(f'Cannot find absolute path to GLOG in CMake find script for Ceres-Solver: {src}')

        with open(dst, 'w') as f: f.write(data)

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

        self.cpp_info.libs = tools.collect_libs(self)

# vim: ts=4 sw=4 expandtab ffs=unix ft=python foldmethod=marker :
