#!/usr/bin/env python

import os
# on Windows, we need the original PATH without Anaconda's compiler in it:
PATH = os.environ.get('PATH', '')
from distutils.spawn import find_executable
from setuptools import setup, find_packages, Extension
import distutils.ccompiler
import sys
import sysconfig
import numpy as np


nvcc_flags = os.environ.get('NVCCFLAGS', '').split()

if os.name == 'nt' and not '--compiler-bindir' in ''.join(nvcc_flags):
    dirname = os.path.dirname(find_executable("cl.exe", PATH) or '')
    if dirname:
        nvcc_flags.extend(['--compiler-bindir', dirname])
    else:
        import warnings
        warnings.warn("MSVC (cl.exe) not found on PATH. Compilation may "
                      "fail. Either set PATH to include the path to MSVC, "
                      "or set NVCCFLAGS=--compiler-bindir=... to define "
                      "it. Possibly also set NVCCFLAGS=--cl-version=2010 "
                      "to override nvcc's MSVC version detection.")
nvcc_flags.extend(['-arch=sm_30', '--ptxas-options=-v', '-c'])

cuda_path = os.environ.get('CUDA_PATH')
libs = ['cudart', 'python27']
libs_dirs = [os.path.join(cuda_path, 'lib/x64')]
libs_dirs.extend([os.path.normpath(r"C:\Users\Edoardo\Anaconda3\envs\tigre\libs")])


# Obtain the numpy include directory.  This logic works across numpy versions.
try:
    numpy_include = np.get_include()
except AttributeError:
    numpy_include = np.get_numpy_include()


# We define a compiler for the extensions defined above:
class NVCCCompiler(distutils.ccompiler.CCompiler):
    """
    Custom CCompiler class that invokes nvcc no matter what.
    """
    compiler_type = 'nvcc'
    executables = {}
    src_extensions = ('.cu','.cpp')
    obj_extension = '.o' if os.name != 'nt' else '.obj'
    shared_lib_extension = sysconfig.get_config_var('SO')

    def _compile(self, obj, src, ext, cc_args, extra_postargs, pp_opts):
        assert ext == '.cu' or ext == '.cpp'
        cmd = ['nvcc', '-O'] + cc_args + [src, '-o', obj] + (
            ['--compiler-options=-fPIC'] if os.name != 'nt' else []) + extra_postargs + pp_opts
        self.spawn(cmd)

    def link(self, target_desc, objects, output_filename, output_dir=None,
             libraries=None, library_dirs=None, runtime_library_dirs=None,
             export_symbols=None, debug=0, extra_preargs=None,
             extra_postargs=None, build_temp=None, target_lang=None):
        if output_dir is not None:
            output_filename = os.path.join(output_dir, output_filename)
        self.mkpath(os.path.dirname(output_filename))
        self.spawn(['nvcc'] + (extra_preargs or []) +
                   ['--shared', '-o', output_filename] + objects +
                   list('-l%s' % lib for lib in libraries
                        if not lib.startswith('python')) +
                   list('-L%s' % libdir for libdir in library_dirs) +
                   (extra_postargs or []) + (['-G'] if debug else []))


# We want setuptools to use NVCCCompiler. The compiler is instantiated in
# build_ext.run(), so we could write a custom build_ext command for this.
# However, build_ext.run() does a lot of other stuff, so we would have to
# copy the full method. To avoid this, we monkey-patch the function used
# to instantiate the compiler at the beginning of build_ext.run():

def new_compiler(plat=None, compiler=None, verbose=0, dry_run=0, force=0):
    return NVCCCompiler(verbose, dry_run, force)

distutils.ccompiler.new_compiler = new_compiler



Ax_ext = Extension('_Ax',
                   sources=(['tigre/Source/projection.cpp',
                             'tigre/Source/Siddon_projection.cu', 'tigre/Source/Siddon_projection_parallel.cu',
                             'tigre/Source/ray_interpolated_projection.cu', 'tigre/Source/ray_interpolated_projection_parallel.cu',
                             'tigre/Source/_types.pxd',
                             'tigre/Source/_Ax.pyx']),
                   library_dirs=libs_dirs,
                   libraries=libs,
                   runtime_library_dirs=libs_dirs,
                   language='c++',
                   extra_compile_args=nvcc_flags,
                   include_dirs=[numpy_include, 'tigre/Source'])

Atb_ext = Extension('_Atb',
                    sources=(['tigre/Source/voxel_backprojection.cu', 'tigre/Source/voxel_backprojection2.cu',
                              'tigre/Source/voxel_backprojection_parallel.cu',
                              'tigre/Source/_types.pxd',
                              'tigre/Source/_Atb.pyx']),
                    library_dirs=libs_dirs,
                    libraries=libs,
                    runtime_library_dirs=libs_dirs,
                    language='c++',
                    extra_compile_args=nvcc_flags,
                    include_dirs=[numpy_include, 'tigre/Source'])

ext_mods = [Ax_ext, Atb_ext]

setup(name='tigre',
      version = '0.0.0',
      author = 'Reuben Lindroos',
      packages = find_packages(),
      include_package_data=True,
      ext_modules=ext_mods,

      # since the package has c code, the egg cannot be zipped
      zip_safe=False)


