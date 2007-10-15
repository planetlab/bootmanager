#!/bin/bash
#
# Build PlanetLab-Bootstrap.tar.bz2, the reference image for PlanetLab
# nodes.
#
# Mark Huang <mlhuang@cs.princeton.edu>
# Copyright (C) 2005-2006 The Trustees of Princeton University
#
# $Id: buildnode.sh,v 1.12.6.1 2007/08/30 20:09:20 mef Exp $
#

PATH=/sbin:/bin:/usr/sbin:/usr/bin

# In both a normal CVS environment and a PlanetLab RPM
# build environment, all of our dependencies are checked out into
# directories at the same level as us.
if [ -d ../../build ] ; then
    PATH=$PATH:../../build
    srcdir=../..
else
    echo "Error: Could not find $(cd ../.. && pwd -P)/build/"
    exit 1
fi

export PATH

. build.common

pl_process_fedora_options $@
shiftcount=$?
shift $shiftcount

# Do not tolerate errors
set -e

VROOT=$PWD/PlanetLab-Bootstrap
install -d -m 755 $VROOT

# Some of the PlanetLab RPMs attempt to (re)start themselves in %post,
# unless the installation is running inside the BootCD environment. We
# would like to pretend that we are.
export PL_BOOTCD=1

# Install the "PlanetLab" group. This requires that the PlanetLab
# build system install the appropriate yumgroups.xml file (currently
# build/groups/v3_yumgroups.xml) in $RPM_BUILD_DIR/../RPMS/ and that
# mkfedora runs either yum-arch or createrepo on that directory. dev
# is specified explicitly because of a stupid bug in its %post script
# that causes its installation to fail; see the mkfedora script for a
# full explanation. coreutils and python are specified explicitly
# because groupinstall does not honor Requires(pre) dependencies
# properly, most %pre scripts require coreutils to be installed first,
# and some of our %post scripts require python.

packagelist=(
filesystem
udev
coreutils
python
)
# vserver-reference packages used for reference image
for package in "${packagelist[@]}" ; do
    packages="$packages -p $package"
done

# Populate VROOT with the files for the PlanetLab-Bootstrap content
pl_setup_chroot $VROOT -k $packages -g PlanetLab

# Disable additional unnecessary services
echo "* Disabling unnecessary services"
for service in netfs rawdevices cpuspeed smartd ; do
    if [ -x $VROOT/etc/init.d/$service ] ; then
	/usr/sbin/chroot $VROOT /sbin/chkconfig $service off
    fi
done

# Build tarball
echo "* Building bootstrap tarball"
tar -cpjf PlanetLab-Bootstrap.tar.bz2 -C $VROOT .

exit 0
