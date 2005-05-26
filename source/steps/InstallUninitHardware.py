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
    Unitializes hardware:
    - unmount all previously mounted partitions

    Except the following variables from the store:
    TEMP_PATH         the path to download and store temp files to
    SYSIMG_PATH       the path where the system image will be mounted
                      (always starts with TEMP_PATH)
    PARTITIONS        dictionary of generic part. types (root/swap)
                      and their associated devices.
    NODE_ID           the node_id from the database for this node

                      this is needed to make any requests back to the server

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

        NODE_ID= vars["NODE_ID"]
        if NODE_ID == "":
            raise ValueError("NODE_ID")

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

    # workaround
    utils.sysexec_noerr( "chroot %s umount /rcfs" % SYSIMG_PATH, log )
            
    log.write( "Unmounting proc.\n" )
    utils.sysexec( "umount %s/proc" % SYSIMG_PATH, log )

    log.write( "Unmounting vserver partition.\n" )
    utils.sysexec( "umount %s" % PARTITIONS["vservers"], log )

    log.write( "Unmounting rcfs file system in image.\n" )
    utils.sysexec_noerr( "chroot %s umount /rcfs" % SYSIMG_PATH, log )

    log.write( "Unmounting system image.\n" )
    utils.sysexec( "umount %s" % PARTITIONS["root"], log )

    log.write( "Shutting down swap\n" )
    utils.sysexec( "swapoff %s" % PARTITIONS["swap"], log )

    # as one of the last steps, upload /var/log/messages if it exists

    # send a notification that the install is complete
    #action= "email"
    #message= "installfinished"
    #nodestate= ""
    
    #try:
    #    result= utils.notifybootserver( BS_REQUEST, NODE_ID,
    #                                         NODE_NONCE,
    #                                         action, message, nodestate )
    #except AlpinaError, desc:
    #    log.write( "Unable to notify boot server of " \
    #                   "install complete (not critical): %s" % desc )
        
    return 1
