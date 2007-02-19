#!/usr/bin/python2 -u

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

    # mkinitrd attempts to determine if the root fs is on a logical
    # volume by checking if the root device contains /dev/mapper in
    # its path. The device node must exist for the check to succeed,
    # but since it's usually managed by devfs or udev, so is probably
    # not present, we just create a dummy file.
    
    fake_root_lvm= False
    if not os.path.exists( "%s/%s" % (SYSIMG_PATH,PARTITIONS["mapper-root"]) ):
        fake_root_lvm= True
        utils.makedirs( "%s/dev/mapper" % SYSIMG_PATH )
        rootdev= file( "%s/%s" % (SYSIMG_PATH,PARTITIONS["mapper-root"]), "w" )
        rootdev.close()

    initrd, kernel_version= systeminfo.getKernelVersion(vars,log)
    utils.removefile( "%s/boot/%s" % (SYSIMG_PATH, initrd) )
    if checkKern() == True:
        utils.sysexec( "chroot %s mkinitrd -v /boot/initrd-%s.img %s" % \
                   (SYSIMG_PATH, kernel_version, kernel_version), log )
    else:
        shutil.copy("./mkinitrd.sh","%s/tmp/mkinitrd.sh" % SYSIMG_PATH)
        os.chmod("%s/tmp/mkinitrd.sh" % SYSIMG_PATH, 755)
        utils.sysexec( "chroot %s /tmp/mkinitrd.sh %s" % (SYSIMG_PATH, kernel_version))

    if fake_root_lvm == True:
        utils.removefile( "%s/%s" % (SYSIMG_PATH,PARTITIONS["mapper-root"]) )

def checkKern():
    #  Older bootcds only support LinuxThreads.  This hack is to get mkinitrd
    #  to run without segfaulting by using /lib/obsolete/linuxthreads
    kver = os.popen("/bin/uname -r", "r").readlines()[0].rstrip().split(".")
    if int(kver[1]) > 4:
        return True
    elif int(kver[1]) <=4:
        return False
