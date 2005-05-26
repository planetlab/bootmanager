# Copyright (c) 2003 Intel Corporation
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:

#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.

#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.

#     * Neither the name of the Intel Corporation nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE INTEL OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# EXPORT LAWS: THIS LICENSE ADDS NO RESTRICTIONS TO THE EXPORT LAWS OF
# YOUR JURISDICTION. It is licensee's responsibility to comply with any
# export regulations applicable in licensee's jurisdiction. Under
# CURRENT (May 2000) U.S. export regulations this software is eligible
# for export from the U.S. and can be downloaded by or otherwise
# exported or reexported worldwide EXCEPT to U.S. embargoed destinations
# which include Cuba, Iraq, Libya, North Korea, Iran, Syria, Sudan,
# Afghanistan and any other country to which the U.S. has embargoed
# goods and services.



import os, sys, shutil
import string

import utils


def Run( vars, log ):
    """
    Setup the install environment:
    - unmount anything in the temp/sysimg path (possible from previous
      aborted installs
    - create temp directories
    
    Expect the following variables from the store:
    TEMP_PATH         the path to download and store temp files to
    SYSIMG_DIR        the directory name of the system image
                      contained in TEMP_PATH
    PLCONF_DIR        The directory to store the configuration file in
    ALPINA_SERVER_DIR The dir on the server where the support files are
    
    Sets the following variables:
    SYSIMG_PATH    the directory where the system image will be mounted,
                   (= TEMP_PATH/SYSIMG_DIR)
    """

    log.write( "\n\nStep: Install: Initializing.\n" )
    
    # make sure we have the variables we need
    try:
        TEMP_PATH= vars["TEMP_PATH"]
        if TEMP_PATH == "":
            raise ValueError("TEMP_PATH")

        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError("SYSIMG_PATH")

        PLCONF_DIR= vars["PLCONF_DIR"]
        if PLCONF_DIR == "":
            raise ValueError, "PLCONF_DIR"

        ALPINA_SERVER_DIR= vars["ALPINA_SERVER_DIR"]
        if ALPINA_SERVER_DIR == "":
            raise ValueError, "ALPINA_SERVER_DIR"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var

    # if this is a fresh install, then nothing should be
    # here, but we support restarted installs without rebooting
    # so who knows what the current state is

    log.write( "Unmounting any previous mounts\n" )
    utils.sysexec_noerr( "chroot %s umount /rcfs" % SYSIMG_PATH, log )
    utils.sysexec_noerr( "umount %s/proc" % SYSIMG_PATH, log )
    utils.sysexec_noerr( "umount %s/mnt/cdrom" % SYSIMG_PATH, log )
    utils.sysexec_noerr( "umount %s/vservers" % SYSIMG_PATH, log )
    utils.sysexec_noerr( "umount %s" % SYSIMG_PATH, log )
    
    log.write( "Removing any old files, directories\n" )
    utils.removedir( TEMP_PATH )
    
    log.write( "Cleaning up any existing PlanetLab config files\n" )
    utils.removedir( PLCONF_DIR )
    
    # create the temp path and sysimg path. since sysimg
    # path is in temp path, both are created here
    log.write( "Creating system image path\n" )
    utils.makedirs( SYSIMG_PATH )

    return 1
