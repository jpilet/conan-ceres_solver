import os
from conans import ConanFile, CMake, tools


class CeresSolverConan(ConanFile):
    name = 'ceres-solver'
    version = '1.11.0'
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

    def package(self):
        pass

    def package_info(self):
        pass

# vim: ts=4 sw=4 expandtab ffs=unix ft=python foldmethod=marker :
