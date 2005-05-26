import os

import InstallWriteConfig
import InstallBuildVServer
from Exceptions import *
import utils



def Run( vars, log ):
    """
    Reconfigure a node if necessary, including rewriting any network init
    scripts based on what PLC has. Also, update any slivers on the machine
    incase their network files are out of date (primarily /etc/hosts).

    This step expects the root to be already mounted on SYSIMG_PATH.
    
    Except the following keys to be set:
    SYSIMG_PATH              the path where the system image will be mounted
                             (always starts with TEMP_PATH)
    ROOT_MOUNTED             the node root file system is mounted
    NETWORK_SETTINGS  A dictionary of the values from the network
                                configuration file
    """
    
    log.write( "\n\nStep: Updating node configuration.\n" )

    # make sure we have the variables we need
    try:
        NETWORK_SETTINGS= vars["NETWORK_SETTINGS"]
        if NETWORK_SETTINGS == "":
            raise ValueError, "NETWORK_SETTINGS"

        SYSIMG_PATH= vars["SYSIMG_PATH"]
        if SYSIMG_PATH == "":
            raise ValueError, "SYSIMG_PATH"

        ROOT_MOUNTED= vars["ROOT_MOUNTED"]
        if ROOT_MOUNTED == "":
            raise ValueError, "ROOT_MOUNTED"

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

    
    if not ROOT_MOUNTED:
        raise BootManagerException, "Root isn't mounted on SYSIMG_PATH\n"


    log.write( "Updating node network configuration\n" )
    InstallWriteConfig.write_network_configuration( vars, log )


    log.write( "Updating vserver's /etc/hosts and /etc/resolv.conf files\n" )

    # create a list of the full directory paths of all the vserver images that
    # need to be updated.
    update_path_list= []

    for base_dir in ('/vservers','/vservers/.vcache'):
        try:
            full_dir_path= "%s/%s" % (SYSIMG_PATH,base_dir)
            slices= os.listdir( full_dir_path )

            try:
                slices.remove("lost+found")
            except ValueError, e:
                pass
            
            update_path_list= update_path_list + map(lambda x: \
                                                     full_dir_path+"/"+x,
                                                     slices)
        except OSError, e:
            continue


    log.write( "Updating network configuration in:\n" )
    if len(update_path_list) == 0:
        log.write( "No vserver images found to update.\n" )
    else:
        for base_dir in update_path_list:
            log.write( "%s\n" % base_dir )


    # now, update /etc/hosts and /etc/resolv.conf in each dir if
    # the update flag is there
    for base_dir in update_path_list:
        InstallBuildVServer.update_vserver_network_files(base_dir,vars,log)
        
    return
