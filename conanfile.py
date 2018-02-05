import os, re
from conans import ConanFile, CMake, tools


class CeresSolverConan(ConanFile):
    """ Tested with versions: 1.11.0, 1.13.0 """

    name = 'ceres_solver'
    license = 'http://ceres-solver.org/license.html'
    url = 'http://ceres-solver.org/'
    description = 'A large scale non-linear optimization library'
    settings = 'os', 'compiler', 'build_type', 'arch'
    options = {'shared': [True, False]}
    default_options = 'shared=True'
    generators = 'cmake'

    def system_requirements(self):
        pack_names = None
        if tools.os_info.linux_distro == "ubuntu":
            pack_names = ['libgoogle-glog-dev']

            if self.settings.arch == 'x86':
                full_pack_names = []
                for pack_name in pack_names:
                    full_pack_names += [pack_name + ':i386']
                pack_names = full_pack_names

        if pack_names:
            installer = tools.SystemPackageTool()
            installer.update() # Update the package database
            installer.install(' '.join(pack_names)) # Install the package

    def requirements(self):
        if '1.11.0' == self.version:
            self.requires('eigen/[>=3.2.0,<3.3.4]@ntc/stable')
        else:
            self.requires('eigen/[>=3.2.0]@ntc/stable')


    def source(self):
        self.run(f'git clone https://ceres-solver.googlesource.com/ceres-solver {self.name}')
        self.run(f'cd {self.name} && git checkout {self.version}')

    def build(self):

        args = []
        args.append('-DCMAKE_CXX_FLAGS="-mtune=generic"')
        args.append('-DBUILD_SHARED_LIBS=%s'%('TRUE' if self.options.shared else 'FALSE'))
        args.append('-DCXX11:BOOL=On')
        args.append('-DNO_CMAKE_PACKAGE_REGISTRY:BOOL=On')
        args.append('-DEIGEN_INCLUDE_DIR:PATH=%s'%os.path.join(self.deps_cpp_info['eigen'].rootpath, 'include', 'eigen3'))
        args.append('-DEigen3_DIR:PATH=%s'%os.path.join(self.deps_cpp_info['eigen'].rootpath, 'share', 'eigen3', 'cmake'))
        args.append('-Wno-dev')

        cmake = CMake(self)
        cmake.configure(source_folder=self.name, args=args)
        cmake.build()
        cmake.install()

        version_major = int(self.version.split('.')[1])
        if version_major < 13:
            path = os.path.join('share', 'Ceres')
        else:
            path = os.path.join('lib', 'cmake', 'Ceres')
        self.fixFindPackage(os.path.join(self.package_folder, path, 'CeresConfig.cmake'))

    def fixFindPackage(self, path):
        """ Remove absolute paths from the CMake file """

        if not os.path.exists(path):
            self.output.warn(f'Cannot find CMake find script for Ceres-Solver: {path}')
            return

        with open(path) as f: data = f.read()

        regex = r'Eigen[^\s]+ (?P<base>.*.data.eigen.(?P<version>\d+.\d+.\d+).*?[a-z0-9]{40})'
        m = re.search(regex, data, re.IGNORECASE)
        if not m:
            self.output.warn(f'Cannot find absolute path to Eigen in CMake find script for Ceres-Solver: {path}')
            return

        data = data.replace(m.group('base'), '${CONAN_EIGEN_ROOT}')
        data = data.replace(m.group('version'), self.deps_cpp_info['eigen'].version)

        with open(path, 'w') as f: f.write(data)

    def package(self):
        pass

    def package_info(self):
        # The CMake files move in different versions, so we're going to use the
        # resdir to point to these.
        version_major = int(self.version.split('.')[1])
        if version_major < 13:
            self.cpp_info.resdirs.append(os.path.join('share', 'Ceres'))
        else:
            self.cpp_info.resdirs.append(os.path.join('lib', 'cmake', 'Ceres'))

# vim: ts=4 sw=4 expandtab ffs=unix ft=python foldmethod=marker :
