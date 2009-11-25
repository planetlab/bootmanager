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
import traceback 

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

    bs_request= BootServerRequest.BootServerRequest(vars)
    
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

    # check deployment (if it's alpha?)
    deployment = ""
    try:
        node_tag_ids = BootAPI.call_api_function(vars, "GetNodes", (NODE_ID,))[0]['node_tag_ids']
        node_tags = BootAPI.call_api_function(vars, "GetNodeTags", (node_tag_ids,))
        deployment_tag = [x for x in node_tags if x['tagname'] == 'deployment']
        if deployment_tag:
            deployment = deployment_tag[0]['value']
    except:
        log.write("WARNING : Failed to query tag 'deployment'\n")
        log.write(traceback.format_exc())

    # which extensions are we part of ?
    utils.breakpoint("Checking for the extension(s) tags")
    extensions = []
    try:
        extension_tag = BootAPI.call_api_function(vars, "GetNodeExtensions", (NODE_ID,) )
        if extension_tag:
            extensions = extension_tag.split()

    except:
        log.write("WARNING : Failed to query tag 'extensions'\n")
        log.write(traceback.format_exc())

    if not extensions:
        log.write("installing only core software\n")
    
    # check if the plain-bootstrapfs tag is set
    download_suffix=".tar.bz2"
    untar_option="-j"
    try:
        if BootAPI.call_api_function (vars, "GetNodePlainBootstrapfs", (NODE_ID,) ):
            download_suffix=".tar"
            untar_option=""
    except:
        log.write("WARNING : Failed to query tag 'plain-bootstrapfs'\n")
        log.write(traceback.format_exc())

    if not untar_option:
        log.write("Using uncompressed bootstrapfs images\n")

    # see also GetBootMedium in PLCAPI that does similar things
    # figuring the default node family:
    # (1) get node's tags 'arch' and 'pldistro'
    # (2) if unsuccessful search /etc/planetlab/nodefamily on the bootcd
    # (3) if that fails, set to planetlab-i386

    try:
        api_pldistro = BootAPI.call_api_function(vars, "GetNodePldistro", (NODE_ID,) )
    except:
        log.write("WARNING : Failed to query tag 'pldistro'\n")
        api_pldistro = None
    try:
        api_arch = BootAPI.call_api_function(vars, "GetNodeArch", (NODE_ID,) )
    except:
        log.write("WARNING : Failed to query tag 'arch'\n")
        api_arch = None
    try:
        (etc_pldistro,etc_arch) = file("/etc/planetlab/nodefamily").read().strip().split("-")
    except:
        log.write("WARNING : Failed to parse /etc/planetlab/nodefamily\n")
        (etc_pldistro,etc_arch)=(None,None)
    default_pldistro="planetlab"
    default_arch="i386"

    if api_pldistro:
        pldistro = api_pldistro
        log.write ("Using pldistro from pldistro API tag\n")
    elif etc_pldistro:
        pldistro = etc_pldistro
        log.write ("Using pldistro from /etc/planetlab/nodefamily\n")
    else:
        pldistro = default_pldistro
        log.write ("Using default pldistro\n")

    if api_arch:
        arch = api_arch
        log.write ("Using arch from arch API tag\n")
    elif etc_arch:
        arch = etc_arch
        log.write ("Using arch from /etc/planetlab/nodefamily\n")
    else:
        arch = default_arch
        log.write ("Using default arch\n")

    log.write ("Using nodefamily=%s-%s\n"%(pldistro,arch))

    bootstrapfs_names = [ pldistro ] + extensions

    # download and extract support tarball for this step, which has
    # everything we need to successfully run

    # we first try to find a tarball, if it is not found we use yum instead
    yum_extensions = []
    # download and extract support tarball for this step, 
    for bootstrapfs_name in bootstrapfs_names:
        tarball = "bootstrapfs-%s-%s%s"%(bootstrapfs_name,arch,download_suffix)
        if len(deployment):
            # we keep bootstrapfs tarballs for deployments in a
            # sub-folder, but with same filenames
            tarball = "%s/%s" %(deployment, tarball)
        source_file= "%s/%s" % (SUPPORT_FILE_DIR,tarball)
        dest_file= "%s/%s" % (SYSIMG_PATH, os.path.basename(tarball))

        # 30 is the connect timeout, 14400 is the max transfer time in
        # seconds (4 hours)
        log.write( "downloading %s\n" % source_file )
        result= bs_request.DownloadFile( source_file, None, None,
                                         1, 1, dest_file,
                                         30, 14400)
        if result:
            log.write( "extracting %s in %s\n" % (dest_file,SYSIMG_PATH) )
            result= utils.sysexec( "tar -C %s -xpf %s %s" % (SYSIMG_PATH,dest_file,untar_option), log )
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
    utils.sysexec_chroot(SYSIMG_PATH, "rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-planetlab")

    # the yum config has changed entirely; 
    # in addition yum installs have more or less never worked - let's forget about this
    # maybe NodeManager could profitably do the job instead
    if yum_extensions:
        log.write("WARNING : yum installs for node extensions are not supported anymore\n")

    return 1
