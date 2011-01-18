#!/usr/bin/python
#
# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.

import os

from Exceptions import *
import utils
import systeminfo

# for centos5.3
# 14:42:27(UTC) No module dm-mem-cache found for kernel 2.6.22.19-vs2.3.0.34.33.onelab, aborting.
# http://kbase.redhat.com/faq/docs/DOC-16528;jsessionid=7E984A99DE8DB094D9FB08181C71717C.ab46478d
def bypassRaidIfNeeded(sysimg_path, log):
    try:
        [ a,b,c,d]=file('%s/etc/redhat-release'%sysimg_path).readlines()[0].strip().split()
        if a !='CentOS': return
        [major,minor]=[int(x) for x in c.split('.')]
        if minor >= 3:
            utils.sysexec_noerr('echo "DMRAID=no" >> %s/etc/sysconfig/mkinitrd/noraid' % sysimg_path , log )
            utils.sysexec_noerr('chmod 755 %s/etc/sysconfig/mkinitrd/noraid' % sysimg_path, log )
    except:
        pass
            
        
def Run( vars, log ):
    """
    Rebuilds the system initrd, on first install or in case the
    hardware changed.
    """

    log.write( "\n\nStep: Rebuilding initrd\n" )
    
    # make sure we have the variables we need
    try:
        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

        PARTITIONS= vars["PARTITIONS"]
        if PARTITIONS == None:
            raise ValueError, "PARTITIONS"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var

    # mkinitrd needs /dev and /proc to do the right thing.
    # /proc is already mounted, so bind-mount /dev here
    # xxx tmp - trying to work around the f14 case:
    # check that /dev/ is mounted with devtmpfs
    # tmp - sysexec_noerr not returning what one would expect
    # if utils.sysexec_noerr ("grep devtmpfs /proc/mounts") != 0:
    utils.sysexec_noerr("mount -t devtmpfs none /dev")
    utils.sysexec("mount -o bind /dev %s/dev" % SYSIMG_PATH)
    utils.sysexec("mount -t sysfs none %s/sys" % SYSIMG_PATH)

    initrd, kernel_version= systeminfo.getKernelVersion(vars,log)
    try:
        utils.removefile( "%s/boot/%s" % (SYSIMG_PATH, initrd) )
    except:
        print "%s/boot/%s is already removed" % (SYSIMG_PATH, initrd)

    # hack for CentOS 5.3
    bypassRaidIfNeeded(SYSIMG_PATH , log )
    # specify ext3 for fedora14 and above as their default fs is ext4
    utils.sysexec_chroot( SYSIMG_PATH, "mkinitrd -v --with=ext3 --allow-missing /boot/initrd-%s.img %s" % \
               (kernel_version, kernel_version), log )

    utils.sysexec_noerr("umount %s/sys" % SYSIMG_PATH , log )
    utils.sysexec_noerr("umount %s/dev" % SYSIMG_PATH , log)

