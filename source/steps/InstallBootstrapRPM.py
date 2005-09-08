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



import os, sys, string
import popen2

from Exceptions import *
import utils
import BootServerRequest


def Run( vars, log ):
    """
    Download enough files to run rpm and yum from a chroot in
    the system image directory
    
    Expect the following variables from the store:
    SYSIMG_PATH          the path where the system image will be mounted
    PARTITIONS           dictionary of generic part. types (root/swap)
                         and their associated devices.
    SUPPORT_FILE_DIR     directory on the boot servers containing
                         scripts and support files
    NODE_ID              the id of this machine
    
    Sets the following variables:
    TEMP_BOOTCD_PATH     where the boot cd is remounted in the temp
                         path
    ROOT_MOUNTED         set to 1 when the the base logical volumes
                         are mounted.
    """

    log.write( "\n\nStep: Install: Bootstrapping RPM.\n" )

    # make sure we have the variables we need
    try:
        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

        PARTITIONS= vars["PARTITIONS"]
        if PARTITIONS == None:
            raise ValueError, "PARTITIONS"

        SUPPORT_FILE_DIR= vars["SUPPORT_FILE_DIR"]
        if SUPPORT_FILE_DIR == None:
            raise ValueError, "SUPPORT_FILE_DIR"

        NODE_ID= vars["NODE_ID"]
        if NODE_ID == "":
            raise ValueError, "NODE_ID"

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
        log.write( "Missing partition in PARTITIONS: %s\n" % part )
        return 0   

    bs_request= BootServerRequest.BootServerRequest()
    
    log.write( "turning on swap space\n" )
    utils.sysexec( "swapon %s" % PARTITIONS["swap"], log )

    # make sure the sysimg dir is present
    utils.makedirs( SYSIMG_PATH )

    log.write( "mounting root file system\n" )
    utils.sysexec( "mount -t ext3 %s %s" % (PARTITIONS["root"],SYSIMG_PATH), log )

    log.write( "mounting vserver partition in root file system\n" )
    utils.makedirs( SYSIMG_PATH + "/vservers" )
    utils.sysexec( "mount -t ext3 %s %s/vservers" % (PARTITIONS["vservers"],
                                                     SYSIMG_PATH), log )

    vars['ROOT_MOUNTED']= 1
    

    # download and extract support tarball for
    # this step, which has everything
    # we need to successfully run
    step_support_file= "PlanetLab-Bootstrap.tar.bz2"
    source_file= "%s/%s" % (SUPPORT_FILE_DIR,step_support_file)
    dest_file= "%s/%s" % (SYSIMG_PATH, step_support_file)

    # 30 is the connect timeout, 7200 is the max transfer time
    # in seconds (2 hours)
    log.write( "downloading %s\n" % step_support_file )
    result= bs_request.DownloadFile( source_file, None, None,
                                          1, 1, dest_file,
                                          30, 7200)
    if not result:
        raise BootManagerException, "Unable to download %s from server." % \
              source_file

    log.write( "extracting %s in %s\n" % (dest_file,SYSIMG_PATH) )
    result= utils.sysexec( "tar -C %s -xpjf %s" % (SYSIMG_PATH,dest_file), log )
    utils.removefile( dest_file )

    # get the yum configuration file for this node (yum.conf).
    # this needs to come from the configuration file service,
    # so, if its a beta node, it'll install the beta rpms from
    # the beginning. The configuration file service will return
    # the url for the file we need to request to get the actual
    # conf file, so two requests need to be made.

    # the only changes we will need to make to it are to change
    # the cache and log directories, so when we run yum from
    # the chrooted tempfs mount, it'll cache the rpms on the
    # sysimg partition

    log.write( "Fetching URL for yum.conf from configuration file service\n" )

    postVars= {"node_id" : NODE_ID,
               "file" : "/etc/yum.conf"}

    yum_conf_url_file= "/tmp/yumconf.url"

    result= bs_request.DownloadFile(
        "/db/plnodeconf/getsinglefile.php",
        None, postVars, 1, 1, yum_conf_url_file)
    
    if result == 0:
        log.write( "Unable to make request to get url for yum.conf\n" )
        return 0

    try:
        yum_conf_url= file(yum_conf_url_file,"r").read()
        yum_conf_url= string.strip(yum_conf_url)
        if yum_conf_url == "":
            raise BootManagerException, \
                  "Downloaded yum configuration file URL is empty."
    except IOError:
        raise BootManagerException, \
              "Unable to open downloaded yum configuration file URL."

    # now, get the actual contents of yum.conf for this node
    log.write( "Fetching yum.conf contents from configuration file service\n" )

    postVars= {}
    download_file_loc= "%s/etc/yum.conf" % SYSIMG_PATH

    result= bs_request.DownloadFile( yum_conf_url,
                                     None, postVars, 1, 1,
                                     download_file_loc)

    if result == 0:
        log.write( "Unable to make request to get yum.conf\n" )
        return 0

    # copy resolv.conf from the base system into our temp dir
    # so DNS lookups work correctly while we are chrooted
    log.write( "Copying resolv.conf to temp dir\n" )
    utils.sysexec( "cp /etc/resolv.conf %s/etc/" % SYSIMG_PATH, log )

    # mount the boot cd in the temp path, under /mnt/cdrom. this way,
    # we can use the certs when programs are running
    # chrooted in the temp path
    cdrom_mount_point= "%s/mnt/cdrom" % SYSIMG_PATH
    utils.makedirs( cdrom_mount_point )
    log.write( "Copying contents of /usr/bootme to /mnt/cdrom\n" )
    utils.sysexec( "cp -r /usr/bootme %s/mnt/cdrom/" % SYSIMG_PATH, log )

    return 1
