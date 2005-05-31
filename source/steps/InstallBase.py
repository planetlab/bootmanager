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


import os

from Exceptions import *
import utils


def Run( vars, log ):
    """
    Install the base system group of RPMs

    Except the following variables from the store:
    TEMP_PATH             the path to download and store temp files to
    SYSIMG_PATH           the path where the system image will be mounted
                          (always starts with TEMP_PATH)
    INSTALL_LANGS         languages for install (used by rpm)
                         
    Sets the following variables:
    None
    
    """

    log.write( "\n\nStep: Install: Installing base OS.\n" )
            
    # make sure we have the variables we need
    try:
        TEMP_PATH= vars["TEMP_PATH"]
        if TEMP_PATH == "":
            raise ValueError, "TEMP_PATH"

        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

        INSTALL_LANGS= vars["INSTALL_LANGS"]
        if INSTALL_LANGS == "":
            raise ValueError, "INSTALL_LANGS"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var
        

    # this will prevent all the locales from being installed
    log.write( "Setting up RPM configuration in sysimg\n" )
    utils.makedirs( "%s/etc/rpm" % SYSIMG_PATH )
    rpm_macros= file( "%s/etc/rpm/macros" % SYSIMG_PATH, "w" )
    rpm_macros.write( "%%_install_langs %s\n" % INSTALL_LANGS )
    rpm_macros.write( "%_excludedocs 1\n" )
    rpm_macros.write( "%__file_context_path /dev/null\n" )
    rpm_macros.close()
    rpm_macros= None

    log.write( "Running base group install using yum\n" )

    # groupupdate instead of groupinstall since BootstrapRPM
    # already installed a pre-configured RPM
    # database. 'PlanetLab' is now a subset of Fedora Core 2
    # Core/Base plus PlanetLab specific RPMs, so that we don't
    # have to run yum multiple times. The group is called
    # 'PlanetLab' for backward compatibility with NodeUpdate,
    # which is hard-coded to update the 'PlanetLab' group.
    yum_cmd= "chroot %s yum --sslcertdir %s -y groupupdate 'PlanetLab'" % \
             (SYSIMG_PATH, CACERT_PATH)

    utils.sysexec( yum_cmd, log );
    
    return 1
