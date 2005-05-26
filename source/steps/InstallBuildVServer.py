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
import string

from Exceptions import *
import utils


# if this file is present in the vservers /etc directory,
# the resolv.conf and hosts files will automatically be updated
# by the bootmanager
UPDATE_FILE_FLAG= "AUTO_UPDATE_NET_FILES"

# the name of the vserver-reference directory
VSERVER_REFERENCE_DIR_NAME='vserver-reference'


def Run( vars, log ):
    """
    Setup directories for building vserver reference image.

    Except the following variables from the store:
    SYSIMG_PATH        the path where the system image will be mounted
                       (always starts with TEMP_PATH)
    NETWORK_SETTINGS   A dictionary of the values from the network
                       configuration file
    
    Sets the following variables:
    None
    
    """

    log.write( "\n\nStep: Install: Setting up VServer image.\n" )

    # make sure we have the variables we need
    try:
        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

        NETWORK_SETTINGS= vars["NETWORK_SETTINGS"]
        if NETWORK_SETTINGS == "":
            raise ValueError, "NETWORK_SETTINGS"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var    

    vserver_ref_dir= "/vservers/vserver-reference"        
    full_vserver_ref_path= "%s/%s" % (SYSIMG_PATH,vserver_ref_dir)

    utils.makedirs( full_vserver_ref_path )
    utils.makedirs( "%s/etc" % full_vserver_ref_path )
    
    log.write( "Setting permissions on directories\n" )
    utils.sysexec( "chmod 0000 %s/vservers/" % SYSIMG_PATH, log )

    return 1



def update_vserver_network_files( vserver_dir, vars, log ):
    """
    Update the /etc/resolv.conf and /etc/hosts files in the specified
    vserver directory. If the files do not exist, write them out. If they
    do exist, rewrite them with new values if the file UPDATE_FILE_FLAG
    exists it /etc. if this is called with the vserver-reference directory,
    always update the network config files and create the UPDATE_FILE_FLAG.

    This is currently called when setting up the initial vserver reference,
    and later when nodes boot to update existing vserver images.

    Expect the following variables from the store:
    SYSIMG_PATH        the path where the system image will be mounted
                       (always starts with TEMP_PATH)
    NETWORK_SETTINGS   A dictionary of the values from the network
                       configuration file
    """

    try:
        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

        NETWORK_SETTINGS= vars["NETWORK_SETTINGS"]
        if NETWORK_SETTINGS == "":
            raise ValueError, "NETWORK_SETTINGS"

    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var

    try:
        ip= NETWORK_SETTINGS['ip']
        method= NETWORK_SETTINGS['method']
        hostname= NETWORK_SETTINGS['hostname']
        domainname= NETWORK_SETTINGS['domainname']
    except KeyError, var:
        raise BootManagerException, \
              "Missing network value %s in var NETWORK_SETTINGS\n" % var

    try:
        os.listdir(vserver_dir)
    except OSError:
        log.write( "Directory %s does not exist to write network conf in.\n" %
                   vserver_dir )
        return

    file_path= "%s/etc/%s" % (vserver_dir,UPDATE_FILE_FLAG)
    update_files= 0
    if os.access(file_path,os.F_OK):
        update_files= 1

        
    if vserver_dir.find(VSERVER_REFERENCE_DIR_NAME) != -1:
        log.write( "Forcing update on vserver-reference directory:\n%s\n" %
                   vserver_dir )
        utils.sysexec_noerr( "echo '%s' > %s/etc/%s" %
                             (UPDATE_FILE_FLAG,vserver_dir,UPDATE_FILE_FLAG),
                             log )
        update_files= 1
        

    if update_files:
        log.write( "Updating network files in %s.\n" % vserver_dir )
        
        file_path= "%s/etc/hosts" % vserver_dir
        hosts_file= file(file_path, "w" )
        hosts_file.write( "127.0.0.1       localhost\n" )
        if method == "static":
            hosts_file.write( "%s %s.%s\n" % (ip, hostname, domainname) )
            hosts_file.close()
            hosts_file= None


        file_path= "%s/etc/resolv.conf" % vserver_dir
        if method == "dhcp":
            # copy the resolv.conf from the boot cd env.
            utils.sysexec( "cp /etc/resolv.conf %s/etc" % vserver_dir, log )
        else:
            # copy the generated resolv.conf from the system image, since
            # we generated it via static settings
            utils.sysexec( "cp %s/etc/resolv.conf %s/etc" % \
                           (SYSIMG_PATH,vserver_dir), log )
            
    return 
