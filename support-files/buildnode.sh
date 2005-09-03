#!/bin/bash
#
# Build PlanetLab-Bootstrap.tar.bz2, the reference image for PlanetLab
# nodes. Requires the web and boot servers to be up, which complicates
# bootstrap. Alternatively, we could require the build server to host
# a local yum repository. Already, it is required to run the same
# major version of yum as the nodes.
#
# Mark Huang <mlhuang@cs.princeton.edu>
# Copyright (C) 2005 The Trustees of Princeton University
#
# $Id$
#

# Get the URL for the production /etc/yum.conf file. XXX When MAs
# begin deploying their own boot servers and/or code, this will have
# to change.
YUM_CONF=http://boot.planet-lab.org/$(curl --silent --insecure --form node_id=0 --form file=/etc/yum.conf https://boot.planet-lab.org/db/plnodeconf/getsinglefile.php)

# Make /
VROOT=$PWD/PlanetLab-Bootstrap
install -d -m 755 $VROOT

MAKEDEV ()
{
    rm -rf $VROOT/dev
    mkdir -p $VROOT/dev
    mknod -m 666 $VROOT/dev/null c 1 3
    mknod -m 666 $VROOT/dev/zero c 1 5
    mknod -m 666 $VROOT/dev/full c 1 7
    mknod -m 644 $VROOT/dev/random c 1 8
    mknod -m 644 $VROOT/dev/urandom c 1 9
    mknod -m 666 $VROOT/dev/tty c 5 0
    mknod -m 666 $VROOT/dev/ptmx c 5 2
    # For bash command substitution
    ln -nsf ../proc/self/fd /dev/fd
    # For df and linuxconf
    touch $VROOT/dev/hdv1
}

# Initialize /dev in reference image
MAKEDEV

# Mount /dev/pts in reference image
mkdir -p $VROOT/dev/pts
mount -t devpts none $VROOT/dev/pts

# Mount /proc in reference image
mkdir -p $VROOT/proc
mount -t proc none $VROOT/proc

# Clean up before exiting if anything goes wrong
trap "umount $VROOT/proc ; umount $VROOT/dev/pts ; exit 255" ERR

# Create a dummy /etc/fstab in reference image
mkdir -p $VROOT/etc
cat > $VROOT/etc/fstab <<EOF
# This fake fstab exists only to please df and linuxconf.
/dev/hdv1	/	ext2	defaults	1 1
EOF
cp $VROOT/etc/fstab $VROOT/etc/mtab

# Prevent all locales from being installed in reference image
mkdir -p $VROOT/etc/rpm
cat > $VROOT/etc/rpm/macros <<EOF
%_install_langs en_US:en
%_excludedocs 1
%__file_context_path /dev/null
EOF

# Trick rpm and yum, who read the real root /etc/rpm/macros file
# rather than the one installed in the reference image, despite what
# you might expect the --root and --installroot options to mean. Both
# programs always read $HOME/.rpmmacros.
export HOME=$PWD
ln -sf $VROOT/etc/rpm/macros $PWD/.rpmmacros

# Initialize RPM database in reference image
mkdir -p $VROOT/var/lib/rpm
rpm --root $VROOT --initdb

# glibc must be specified explicitly for the correct arch to be chosen
yum -c $YUM_CONF --installroot=$VROOT -y install glibc yum

# yum will annoyingly use the /etc/yum.conf file in the --installroot
# even if overridden with -c
rm -f $VROOT/etc/yum.conf

# Some of the PlanetLab RPMs may attempt to call /sbin/runlevel to
# determine if the installation is running inside the BootCD
# environment. We would like to pretend that we are, so make sure
# /sbin/runlevel returns 'unknown'.
rm -f $VROOT/var/run/utmp
export PL_BOOTCD=1

# Go, baby, go
yum -c $YUM_CONF --installroot=$VROOT -y groupinstall PlanetLab

# Freshen the RPM set with any just built. This does not help when a
# completely new PlanetLab package must be installed in the reference
# image. To work around this limitation, introduce the new package in
# one release, then include it in the VServer yumgroup in the next.
if [ -d $RPM_BUILD_DIR/../RPMS ] ; then
    rpm --root $VROOT --freshen --verbose $RPM_BUILD_DIR/../RPMS/*/*.rpm
fi

# Remove stale RPM locks
rm -f $VROOT/var/lib/rpm/__db*

# Clean up /dev in reference image
umount $VROOT/dev/pts

# Disable unnecessary services
for service in netfs rawdevices cpuspeed smartd ; do
    /usr/sbin/chroot $VROOT /sbin/chkconfig $service off
done

# Clean up
umount $VROOT/proc

# Build tarball
tar -cpjf PlanetLab-Bootstrap.tar.bz2 -C $VROOT .
rm -rf $VROOT

exit 0