import os
import sys
from os.path import join
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import setuptools


PL_USE_ROBUST_PREDICATES_NAME = 'PL_USE_ROBUST_PREDICATES'
PL_USE_ROBUST_PREDICATES = int(os.environ.get(PL_USE_ROBUST_PREDICATES_NAME, 0))
if PL_USE_ROBUST_PREDICATES:
    print("Building with robust geometric predicates.")
else:
    print("NOT building with robust predicates")

PL_USE_STD_UNORDERED_MAP_NAME = 'PL_USE_STD_UNORDERED_MAP'
PL_USE_STD_UNORDERED_MAP = int(os.environ.get(PL_USE_STD_UNORDERED_MAP_NAME, 0))
if PL_USE_STD_UNORDERED_MAP:
    print("Building with slower std::unordered_map.")
else:
    print("Building with fast flat_hash_map. 30% Speedup. Does not work with GCC7. See Wiki.")


__version__ = '0.0.4'

class get_pybind_include(object):
    """Helper class to determine the pybind11 include path

    The purpose of this class is to postpone importing pybind11
    until it is actually installed, so that the ``get_include()``
    method can be invoked. """

    def __init__(self, user=False, subdir=False):
        self.user = user

    def __str__(self):
        import pybind11
        include_path = os.path.dirname(pybind11.get_include(self.user))
        subdir = "python%s.%s" % (sys.version_info.major, sys.version_info.minor)
        include_path_sub = join(include_path, subdir)
        if subdir:
            return include_path_sub
        else:
            return include_path

class get_numpy_include(object):
    """Helper class to determine the numpy include path
    The purpose of this class is to postpone importing numpy
    until it is actually installed, so that the ``get_include()``
    method can be invoked. """

    def __init__(self):
        pass

    def __str__(self):
        import numpy as np
        return np.get_include()

# Source files for polylidar
source_files = ['polylidar/module.cpp', 'polylidar/polylidar.cpp', 'polylidar/delaunator.cpp', 'polylidar/helper.cpp']
# Source files for robust geometric predicates
robust_files = ['polylidar/predicates/constants.c', 'polylidar/predicates/predicates.c', 'polylidar/predicates/printing.c', 'polylidar/predicates/random.c']
# Include directories for polylidar
include_dirs = [get_pybind_include(), get_pybind_include(user=True), get_pybind_include(subdir=True), get_numpy_include(), 'polylidar/']

# If compiling with robust predicates then add robust c and header files
if PL_USE_ROBUST_PREDICATES:
    source_files.extend(robust_files)
    include_dirs.append('polylidar/predicates/')

ext_modules = [
    Extension(
        'polylidar',
        source_files,
        include_dirs=include_dirs,
        language='c++'
    ),
]


# As of Python 3.6, CCompiler has a `has_flag` method.
# cf http://bugs.python.org/issue26689
def has_flag(compiler, flagname):
    """Return a boolean indicating whether a flag name is supported on
    the specified compiler.
    """
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.cpp') as f:
        f.write('int main (int argc, char **argv) { return 0; }')
        try:
            compiler.compile([f.name], extra_postargs=[flagname])
        except setuptools.distutils.errors.CompileError:
            return False
    return True


def cpp_flag(compiler):
    """Return the -std=c++[11/14] compiler flag.

    The c++14 is prefered over c++11 (when it is available).
    """
    if has_flag(compiler, '-std=c++14'):
        return '-std=c++14'
    elif has_flag(compiler, '-std=c++11'):
        return '-std=c++11'
    else:
        raise RuntimeError('Unsupported compiler -- at least C++11 support '
                           'is needed!')


class BuildExt(build_ext):
    """A custom build extension for adding compiler-specific options."""
    c_opts = {
        'msvc': ['/EHsc'],
        'unix': [],
    }

    if sys.platform == 'darwin':
        c_opts['unix'] += ['-stdlib=libc++', '-mmacosx-version-min=10.7']

    def build_extensions(self):
        ct = self.compiler.compiler_type
        opts = self.c_opts.get(ct, [])
        opts.append('-DPY_EXTENSION') # inform compiler that we are compiling as a pyextension
        if PL_USE_ROBUST_PREDICATES:
            opts.append('-DPL_USE_ROBUST_PREDICATES')
        if PL_USE_STD_UNORDERED_MAP:
            opts.append('-DPL_USE_STD_UNORDERED_MAP')
        if ct == 'unix':
            opts.append('-DVERSION_INFO="%s"' % self.distribution.get_version())
            opts.append('-Wall')
            opts.append(cpp_flag(self.compiler))
            if has_flag(self.compiler, '-fvisibility=hidden'):
                opts.append('-fvisibility=hidden')
        elif ct == 'msvc':
            opts.append('/DVERSION_INFO=\\"%s\\"' % self.distribution.get_version())
        for ext in self.extensions:
            ext.extra_compile_args = opts
        build_ext.build_extensions(self)


DEV = ['pytest', 'pytest-benchmark', 'pylint', 'twine', 'autopep8', 'nox']

setup(
    name='polylidar',
    version=__version__,
    author='Jeremy Castagno',
    author_email='jdcasta@umich.edu',
    packages=['polylidarutil', 'polylidar'],
    url='',
    description='Polygon extraction from Point Cloud data',
    long_description='',
    ext_modules=ext_modules,
    install_requires=['pybind11>=2.2', 'numpy', 'shapely', 'matplotlib', 'descartes'],
    extras_require={
        'dev': DEV
    },
    cmdclass={'build_ext': BuildExt},
    zip_safe=False,
)
