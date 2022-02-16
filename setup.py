from __future__ import print_function

import os
import pathlib
import platform
import sys
import tarfile

import setuptools
from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext as build_ext_orig

if sys.version_info < (3, ):
    print("Please use Python 3 for nnf python library")
    sys.exit(-1)


python_min_version = (3, 5, 2)
python_min_version_str = '.'.join(map(str, python_min_version))
if sys.version_info < python_min_version:
    print("You are using Python {}. Python >={} is required.".format(
        platform.python_version(), python_min_version_str))
    sys.exit(-1)

nnf_bin = "build/src/tools/nnfusion/nnfusion"
nnf_tool = "build/src/tools/nnfusion/"
nnf_blacklist = ["cmake_install.cmake", "Makefile", "CMakeFiles"]

# if not os.path.exists(nnf_bin):
#     print("Pleast build nnfusion in /build folder.")
#     sys.exit(-1)


def get_data_files(source_dir, ignore_list):
    def dir_files_pair(root, files):
        directory = os.path.relpath(root, source_dir)
        directory = os.path.join('nnfusion-bin', directory)
        files = [
            os.path.join(root, file)
            for file in files
            if file not in ignore_list
        ]
        return directory, files

    pairs = [
        dir_files_pair(root, files)
        for root, dir, files in os.walk(source_dir)
        if not any(word in root for word in ignore_list)
    ]
    # Remove if files is empty
    return [
        pair
        for pair in pairs
        if pair[1]
    ]


class CMakeExtension(Extension):

    def __init__(self, name):
        # don't invoke the original build_ext for this special extension
        super().__init__(name, sources=[])


class build_ext(build_ext_orig):

    def run(self):
        for ext in self.extensions:
            self.build_cmake(ext)
        super().run()

    def build_cmake(self, ext):
        cwd = pathlib.Path().absolute()

        # these dirs will be created in build_py, so if you don't have
        # any python sources to bundle, the dirs will be missing
        build_temp = pathlib.Path(self.build_temp)
        build_temp = pathlib.Path('build')
        print(self.build_temp)
        build_temp.mkdir(parents=True, exist_ok=True)
        extdir = pathlib.Path(self.get_ext_fullpath(ext.name))
        extdir.mkdir(parents=True, exist_ok=True)

        os.chdir(str(build_temp))
        self.spawn(['cmake', str(cwd)])
        if not self.dry_run:
            self.spawn(['make', '-j'])
        # Troubleshooting: if fail on line above then delete all possible
        # temporary CMake files including "CMakeCache.txt" in top level dir.
        os.chdir(str(cwd))


with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt") as f:
    install_requires = f.read().splitlines()

with open("requirements_test.txt") as f:
    tests_require = f.read().splitlines()

with open("VERSION") as f:
    version = f.readline().strip()

setuptools.setup(
    name="nnfusion",
    version=version,
    author="Microsoft Corporation",
    author_email="nnfusion-team@microsoft.com",
    description="NNFusion is a flexible and efficient DNN compiler",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/microsoft/nnfusion",
    packages=setuptools.find_packages(where="src/python", exclude=["example"]),
    package_dir={"": "src/python"},
    data_files=get_data_files(nnf_tool, nnf_blacklist),
    ext_modules=[CMakeExtension('.')],
    cmdclass={
        'build_ext': build_ext,
    },
    install_requires=install_requires,
    tests_require=tests_require,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={
        'console_scripts': [
            'nnfusion=nnfusion.__main__:main',
        ],
    }
)
