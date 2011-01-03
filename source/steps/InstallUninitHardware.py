#!/usr/bin/python
#
# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.
# expected /proc/partitions format

import os

from Exceptions import *
import utils



def Run( vars, log ):
    """
    Unitializes hardware:
    - unmount everything mounted during install, except the
    /dev/planetlab/root and /dev/planetlab/vservers. This includes
    calling swapoff for /dev/planetlab/swap.

    Except the following variables from the store:
    TEMP_PATH         the path to download and store temp files to
    SYSIMG_PATH       the path where the system image will be mounted
                      (always starts with TEMP_PATH)
    PARTITIONS        dictionary of generic part. types (root/swap)
                      and their associated devices.

    Sets the following variables:
    None
    
    """

    log.write( "\n\nStep: Install: Shutting down installer.\n" )

    # make sure we have the variables we need
    try:
        TEMP_PATH= vars["TEMP_PATH"]
        if TEMP_PATH == "":
            raise ValueError, "TEMP_PATH"

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


    try:
        # make sure the required partitions exist
        val= PARTITIONS["root"]
        val= PARTITIONS["swap"]
        val= PARTITIONS["vservers"]
    except KeyError, part:
        raise BootManagerException, "Missing partition in PARTITIONS: %s\n" % part

    try:
        # backwards compat, though, we should never hit this case post PL 3.2
        os.stat("%s/rcfs/taskclass"%SYSIMG_PATH)
        utils.sysexec_chroot_noerr( SYSIMG_PATH, "umount /rcfs", log )
    except OSError, e:
        pass
            
    log.write( "Shutting down swap\n" )
    utils.sysexec( "swapoff %s" % PARTITIONS["swap"], log )

    return 1
