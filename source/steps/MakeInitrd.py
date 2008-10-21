#!/usr/bin/python

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.

import os, string

from Exceptions import *
import utils
import systeminfo
import shutil

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
    utils.sysexec("mount -o bind /dev %s/dev" % SYSIMG_PATH)
    utils.sysexec("mount -t sysfs none %s/sys" % SYSIMG_PATH)

    initrd, kernel_version= systeminfo.getKernelVersion(vars,log)
    utils.removefile( "%s/boot/%s" % (SYSIMG_PATH, initrd) )
    if checkKern() == True:
        utils.sysexec( "chroot %s mkinitrd -v /boot/initrd-%s.img %s" % \
                   (SYSIMG_PATH, kernel_version, kernel_version), log )
    else:
        shutil.copy("./mkinitrd.sh","%s/tmp/mkinitrd.sh" % SYSIMG_PATH)
        os.chmod("%s/tmp/mkinitrd.sh" % SYSIMG_PATH, 755)
        utils.sysexec( "chroot %s /tmp/mkinitrd.sh %s" % (SYSIMG_PATH, kernel_version))

    utils.sysexec_noerr("umount %s/sys" % SYSIMG_PATH)
    utils.sysexec_noerr("umount %s/dev" % SYSIMG_PATH)

def checkKern():
    #  Older bootcds only support LinuxThreads.  This hack is to get mkinitrd
    #  to run without segfaulting by using /lib/obsolete/linuxthreads
    kver = os.popen("/bin/uname -r", "r").readlines()[0].rstrip().split(".")
    if int(kver[1]) > 4:
        return True
    elif int(kver[1]) <=4:
        return False
