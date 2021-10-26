#!/bin/bash -e

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

echo "Running NNFusion install_dependency.sh"
DEB_PACKAGES="build-essential cmake clang-3.9 clang-format-3.9 git curl zlib1g zlib1g-dev libtinfo-dev unzip \
autoconf automake libtool ca-certificates gdb sqlite3 libsqlite3-dev libcurl4-openssl-dev libprotobuf-dev \
protobuf-compiler libgflags-dev libgtest-dev"

if [[ "$(whoami)" != "root" ]]; then
	SUDO=sudo
fi

ubuntu_codename=$(. /etc/os-release;echo $UBUNTU_CODENAME)

if ! dpkg -L $DEB_PACKAGES >/dev/null 2>&1; then
	#Thirdparty deb for ubuntu 18.04(bionic)
	$SUDO sh -c "apt update && apt install -y --no-install-recommends software-properties-common apt-transport-https ca-certificates gnupg wget"
	$SUDO sh -c "wget -O - https://apt.kitware.com/keys/kitware-archive-latest.asc 2>/dev/null | gpg --dearmor - | tee /etc/apt/trusted.gpg.d/kitware.gpg >/dev/null"
	$SUDO sh -c "apt-add-repository 'deb https://apt.kitware.com/ubuntu/ $ubuntu_codename main'"
	$SUDO sh -c "apt update && apt install -y --no-install-recommends $DEB_PACKAGES"

	# Install protobuf 3.6.1 from source
	$SUDO sh -c "wget https://github.com/protocolbuffers/protobuf/releases/download/v3.6.1/protobuf-cpp-3.6.1.tar.gz -P /tmp"
	$SUDO sh -c "cd /tmp && tar -xf /tmp/protobuf-cpp-3.6.1.tar.gz && rm /tmp/protobuf-cpp-3.6.1.tar.gz"
	$SUDO sh -c "cd /tmp/protobuf-3.6.1/ && ./configure && make && make check && make install && ldconfig && rm -rf /tmp/protobuf-3.6.1/"
fi
echo "- Dependencies are installed in system."

if [ ! -f "/usr/lib/libgtest.a" ]; then

	# if Ubuntu 16.04, we have some dev node using ubuntu 16.04
	if [[ $ubuntu_codename == "xenial" ]]; then
		gtest_src_path="/usr/src/gtest"
	else
		gtest_src_path="/usr/src/googletest/googletest"
	fi

	# Compile gtest
	$SUDO sh -c "cd ${gtest_src_path} && mkdir -p  build && cd build && cmake .. -DCMAKE_CXX_FLAGS=\"-std=c++11\" && make -j"
	$SUDO sh -c "cp ${gtest_src_path}/build/libgtest*.a /usr/lib/"
	$SUDO sh -c "rm -rf ${gtest_src_path}/build"
	$SUDO sh -c "rm -rf /usr/src/googletest/googletest/build"

	$SUDO sh -c "mkdir /usr/local/lib/googletest"
	$SUDO sh -c "ln -s /usr/lib/libgtest.a /usr/local/lib/googletest/libgtest.a"
	$SUDO sh -c "ln -s /usr/lib/libgtest_main.a /usr/local/lib/googletest/libgtest_main.a"
fi
echo "- libgtest is installed in system."

echo "- Done."
