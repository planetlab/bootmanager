#!/usr/bin/python

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2007 The Trustees of Princeton University
# All rights reserved.
# expected /proc/partitions format

import os, sys, string
import popen2
import shutil

from Exceptions import *
import utils
import BootServerRequest
import BootAPI


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

    log.write( "\n\nStep: Install: bootstrapfs tarball.\n" )

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

    # which extensions are we part of ?
    utils.breakpoint("Getting the extension tag on node")
    try:
        extension_tag = BootAPI.call_api_function(vars, "GetNodeExtensions", ([NODE_ID]))
        extensions = extension_tag.split()

    except:
        log.write("WARNING : Failed to query the extension tag - installing only core software\n")
        extensions = []
    
    # see also GetBootMedium in PLCAPI that does similar things
    # figuring the default node family:
    # (1) look at /etc/planetlab/nodefamily on the bootcd
    # (2) if that fails, set to planetlab-i386
    try:
        (pldistro,arch) = file("/etc/planetlab/nodefamily").read().strip().split("-")
    except:
        # what arch should be used for this node
        utils.breakpoint("Getting the arch tag on node")
        pldistro="planetlab"
        default_arch="i386"
        try:
            arch = BootAPI.call_api_function(vars, "GetNodeArch", ([NODE_ID]))
        except:
            log.write("WARNING : Failed to query node arch - using %(default_arch)s\n"%locals())
            arch = default_arch

    bootstrapfs_names = [ pldistro ] + extensions

    # download and extract support tarball for this step, which has
    # everything we need to successfully run

    # we first try to find a tarball, if it is not found we use yum instead
    yum_extensions = []
    # download and extract support tarball for this step, 
    for bootstrapfs_name in bootstrapfs_names:
        tarball = "bootstrapfs-%s-%s.tar.bz2"%(bootstrapfs_name,arch)
        source_file= "%s/%s" % (SUPPORT_FILE_DIR,tarball)
        dest_file= "%s/%s" % (SYSIMG_PATH, tarball)

        # 30 is the connect timeout, 14400 is the max transfer time in
        # seconds (4 hours)
        log.write( "downloading %s\n" % source_file )
        result= bs_request.DownloadFile( source_file, None, None,
                                         1, 1, dest_file,
                                         30, 14400)
        if result:
            log.write( "extracting %s in %s\n" % (dest_file,SYSIMG_PATH) )
            result= utils.sysexec( "tar -C %s -xpjf %s" % (SYSIMG_PATH,dest_file), log )
            log.write( "Done\n")
            utils.removefile( dest_file )
        else:
            # the main tarball is required
            if bootstrapfs_name == pldistro:
                raise BootManagerException, "Unable to download main tarball %s from server." % \
                    source_file
            else:
                log.write("tarball for %s-%s not found, scheduling a yum attempt\n"%(bootstrapfs_name,arch))
                yum_extensions.append(bootstrapfs_name)

    # copy resolv.conf from the base system into our temp dir
    # so DNS lookups work correctly while we are chrooted
    log.write( "Copying resolv.conf to temp dir\n" )
    utils.sysexec( "cp /etc/resolv.conf %s/etc/" % SYSIMG_PATH, log )

    # Copy the boot server certificate(s) and GPG public key to
    # /usr/boot in the temp dir.
    log.write( "Copying boot server certificates and public key\n" )

    if os.path.exists("/usr/boot"):
        utils.makedirs(SYSIMG_PATH + "/usr")
        shutil.copytree("/usr/boot", SYSIMG_PATH + "/usr/boot")
    elif os.path.exists("/usr/bootme"):
        utils.makedirs(SYSIMG_PATH + "/usr/boot")
        boot_server = file("/usr/bootme/BOOTSERVER").readline().strip()
        shutil.copy("/usr/bootme/cacert/" + boot_server + "/cacert.pem",
                    SYSIMG_PATH + "/usr/boot/cacert.pem")
        file(SYSIMG_PATH + "/usr/boot/boot_server", "w").write(boot_server)
        shutil.copy("/usr/bootme/pubring.gpg", SYSIMG_PATH + "/usr/boot/pubring.gpg")
        
    # For backward compatibility
    if os.path.exists("/usr/bootme"):
        utils.makedirs(SYSIMG_PATH + "/mnt/cdrom")
        shutil.copytree("/usr/bootme", SYSIMG_PATH + "/mnt/cdrom/bootme")

    # Import the GPG key into the RPM database so that RPMS can be verified
    utils.makedirs(SYSIMG_PATH + "/etc/pki/rpm-gpg")
    utils.sysexec("gpg --homedir=/root --export --armor" \
                  " --no-default-keyring --keyring %s/usr/boot/pubring.gpg" \
                  " >%s/etc/pki/rpm-gpg/RPM-GPG-KEY-planetlab" % (SYSIMG_PATH, SYSIMG_PATH))
    utils.sysexec("chroot %s rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-planetlab" % \
                  SYSIMG_PATH)

    # the yum config has changed entirely; 
    # in addition yum installs have more or less never worked - let's forget about this
    # maybe NodeManager could profitably do the job instead
    if yum_extensions:
        log.write('WARNING : yum installs for node extensions are not supported anymore')

    return 1
