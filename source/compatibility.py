#!/usr/bin/python2

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.


"""
Various functions that are used to allow the boot manager to run on various
different cds are included here
"""

import string
import os, sys

from Exceptions import *
import utils
import BootServerRequest


def setup_lvm_2x_cd( vars, log ):
    """
    make available a set of lvm utilities for 2.x cds that don't have them
    on the cd.

    Expect the following variables to be set:
    TEMP_PATH                somewhere to store what we need to run
    BOOT_CD_VERSION          A tuple of the current bootcd version
    SUPPORT_FILE_DIR         directory on the boot servers containing
                             scripts and support files
    LVM_SETUP_2X_CD          indicates if lvm is downloaded and setup for 2.x cds
    
    Set the following variables upon successfully running:
    LVM_SETUP_2X_CD          indicates if lvm is downloaded and setup for 2.x cds
    """
    
    # make sure we have the variables we need
    try:
        TEMP_PATH= vars["TEMP_PATH"]
        if TEMP_PATH == "":
            raise ValueError, "TEMP_PATH"

        BOOT_CD_VERSION= vars["BOOT_CD_VERSION"]
        if BOOT_CD_VERSION == "":
            raise ValueError, "BOOT_CD_VERSION"

        SUPPORT_FILE_DIR= vars["SUPPORT_FILE_DIR"]
        if SUPPORT_FILE_DIR == None:
            raise ValueError, "SUPPORT_FILE_DIR"
        
    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var


    if BOOT_CD_VERSION[0] != 2:
        log.write( "Only 2.x boot cds need lvm setup manually.\n" )
        return 1
    
    LVM_SETUP_2X_CD= 0
    if 'LVM_SETUP_2X_CD' in vars.keys():
        LVM_SETUP_2X_CD= vars['LVM_SETUP_2X_CD']
        
    if LVM_SETUP_2X_CD:
        log.write( "LVM already downloaded and setup\n" )
        return 1

    log.write( "Downloading additional libraries for lvm\n" )

    bs_request= BootServerRequest.BootServerRequest()
        
    utils.makedirs(TEMP_PATH)

    # download and extract support tarball for this step,
    # which has everything we need to successfully run
    step_support_file= "alpina-BootLVM.tar.gz"
    source_file= "%s/%s" % (SUPPORT_FILE_DIR,step_support_file)
    dest_file= "%s/%s" % (TEMP_PATH, step_support_file)

    log.write( "Downloading support file for this step\n" )
    result= bs_request.DownloadFile( source_file, None, None,
                                     1, 1, dest_file )
    if not result:
        raise BootManagerException, "Download failed."

    log.write( "Extracting support files\n" )
    old_wd= os.getcwd()
    utils.chdir( TEMP_PATH )
    utils.sysexec( "tar -C / -xzf %s" % step_support_file, log )
    utils.removefile( dest_file )
    utils.chdir( old_wd )

    utils.sysexec( "ldconfig", log )

    # load lvm-mod
    log.write( "Loading lvm module\n" )
    utils.sysexec( "modprobe lvm-mod", log )

    # take note that we have lvm setup
    LVM_SETUP_2X_CD= 1
    vars['LVM_SETUP_2X_CD']= LVM_SETUP_2X_CD

    return 1



def setup_partdisks_2x_cd( vars, log ):
    """
    download necessary files to handle partitioning disks on 2.x cds

    Expect the following variables to be set:
    TEMP_PATH                somewhere to store what we need to run
    BOOT_CD_VERSION          A tuple of the current bootcd version
    SUPPORT_FILE_DIR         directory on the boot servers containing
                             scripts and support files
    PARTDISKS_SETUP_2X_CD    indicates if lvm is downloaded and setup for 2.x cds
    
    Set the following variables upon successfully running:
    PARTDISKS_SETUP_2X_CD    indicates if lvm is downloaded and setup for 2.x cds
    """

    # make sure we have the variables we need
    try:
        TEMP_PATH= vars["TEMP_PATH"]
        if TEMP_PATH == "":
            raise ValueError, "TEMP_PATH"

        BOOT_CD_VERSION= vars["BOOT_CD_VERSION"]
        if BOOT_CD_VERSION == "":
            raise ValueError, "BOOT_CD_VERSION"

        SUPPORT_FILE_DIR= vars["SUPPORT_FILE_DIR"]
        if SUPPORT_FILE_DIR == None:
            raise ValueError, "SUPPORT_FILE_DIR"
        
    except KeyError, var:
        raise BootManagerException, "Missing variable in vars: %s\n" % var
    except ValueError, var:
        raise BootManagerException, "Variable in vars, shouldn't be: %s\n" % var


    if BOOT_CD_VERSION[0] != 2:
        log.write( "Only 2.x boot cds need partition disk tools setup manually.\n" )
        return 1

    PARTDISKS_SETUP_2X_CD= 0
    if 'PARTDISKS_SETUP_2X_CD' in vars.keys():
        PARTDISKS_SETUP_2X_CD= vars['PARTDISKS_SETUP_2X_CD']

    if PARTDISKS_SETUP_2X_CD:
        log.write( "Partition disk tools already downloaded and setup\n" )
        return 1

    log.write( "Downloading additional libraries for partitioning disks\n" )

    bs_request= BootServerRequest.BootServerRequest()

    # download and extract support tarball for this step,
    # which has everything we need to successfully run
    step_support_file= "alpina-PartDisks.tar.gz"
    source_file= "%s/%s" % (SUPPORT_FILE_DIR,step_support_file)
    dest_file= "%s/%s" % (TEMP_PATH, step_support_file)

    log.write( "Downloading support file for this step\n" )
    result= bs_request.DownloadFile( source_file, None, None,
                                     1, 1, dest_file )
    if not result:
        raise BootManagerException, "Download failed."

    log.write( "Extracting support files\n" )
    old_wd= os.getcwd()
    utils.chdir( TEMP_PATH )
    utils.sysexec( "tar -xzf %s" % step_support_file, log )
    utils.removefile( dest_file )
    utils.chdir( old_wd )

    # also included in the support package was a list of extra
    # paths (lib-paths) for /etc/ld.so.conf.
    # so add those, and rerun ldconfig
    # so we can make our newly downloaded libraries available

    ldconf_file= file("/etc/ld.so.conf","a+")
    lib_paths_file= file( TEMP_PATH + "/lib-paths","r")

    for line in lib_paths_file:
        path= string.strip(line)
        if path != "":
            ldconf_file.write( "%s/%s\n" % (TEMP_PATH,path) )
    ldconf_file.close()
    lib_paths_file.close()

    utils.sysexec( "ldconfig", log )

    # update the PYTHONPATH to include the python modules in
    # the support package
    sys.path.append( TEMP_PATH + "/usr/lib/python2.2" )
    sys.path.append( TEMP_PATH + "/usr/lib/python2.2/site-packages" )

    # update the environment variable PATH to include
    # TEMP_PATH/sbin and others there
    new_paths= ('%s/sbin'% TEMP_PATH,
                '%s/bin'% TEMP_PATH,
                '%s/user/sbin'% TEMP_PATH,
                '%s/user/bin'% TEMP_PATH)

    old_path= os.environ['PATH']
    os.environ['PATH']= old_path + ":" + string.join(new_paths,":")

    # everything should be setup to import parted. this 
    # import is just to make sure it'll work when this step
    # is being run
    log.write( "Imported parted\n" )
    try:
        import parted
    except ImportError:
        raise BootManagerException, "Unable to import parted."

    # take note that we have part disks setup
    PARTDISKS_SETUP_2X_CD= 1
    vars['PARTDISKS_SETUP_2X_CD']= PARTDISKS_SETUP_2X_CD


    
