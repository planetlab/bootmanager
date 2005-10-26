import os
import xmlrpclib
import socket
import string

from Exceptions import *
import utils


# locations of boot os version files
BOOT_VERSION_2X_FILE='/usr/bootme/ID'
BOOT_VERSION_3X_FILE='/pl_version'

# locations of boot server name/certificate files
V2X_BOOTCD_SERVER_FILE = "/usr/bootme/BOOTSERVER"
V2X_BOOTCD_SERVER_CACERT_DIR = "/usr/bootme/cacert"
V2X_CACERT_NAME = "cacert.pem"
    
V3X_BOOTCD_SERVER_FILE = "/usr/boot/boot_server"
V3X_BOOTCD_SERVER_CACERT = "/usr/boot/cacert.pem"

# minimium version of the boot os we need to run, as a (major,minor) tuple
MINIMUM_BOOT_VERSION= (2,0)

# minimum version of python required to run the boot manager
MINIMUM_PYTHON_VERSION= (2,2,0)


def Run( vars, log ):
    """
    Setup the boot manager so it can run, do any extra necessary
    hardware setup (to fix old cd problems)

    Sets the following variables:
    BOOT_CD_VERSION           A two number tuple of the boot cd version
    MA_BOOT_SERVER            The boot server we contacted, identified from
                              files on the boot cd.
    MA_BOOT_SERVER_CACERT     The SSL certificate for the above server

    """

    log.write( "\n\nStep: Initializing the BootManager.\n" )


    if not __check_boot_version( vars, log ):
        raise BootManagerException, \
              "Boot CD version insufficient to run the Boot Manager"
    else:
        log.write( "Running on boot cd version: %s\n" %
                   str(vars['BOOT_CD_VERSION']) )

    BOOT_CD_VERSION= vars['BOOT_CD_VERSION']


    log.write( "Identifying boot server and setting up /etc/planetlab entries" )

    # need to pull the server name we contacted. 2.x cds will have the
    # info in /usr/bootme; 3.x cds in /usr/boot
    if BOOT_CD_VERSION[0] == 2:
        try:
            boot_server= file(V2X_BOOTCD_SERVER_FILE).readline().strip()                
        except IOError:
            raise BootManagerException, \
                  "It appears we are running on a v2.x boot cd, but could " \
                  "not load contacted boot server from %s" % V2X_BOOTCD_SERVER_FILE
        
        if boot_server == "":
            raise BootManagerException, \
                  "It appears we are running on a v2.x boot cd, but %s " \
                  "appears to be blank." % V2X_BOOTCD_SERVER_FILE

        cacert_file= "%s/%s/%s" % (V2X_BOOTCD_SERVER_CACERT_DIR,
                                   boot_server, V2X_CACERT_NAME)

    elif BOOT_CD_VERSION[0] == 3:
        try:
            boot_server= file(V3X_BOOTCD_SERVER_FILE).read().strip()                
        except IOError:
            raise BootManagerException, \
                  "It appears we are running on a v3.x boot cd, but could " \
                  "not load contacted boot server from %s" % V3X_BOOTCD_SERVER_FILE
        
        if boot_server == "":
            raise BootManagerException, \
                  "It appears we are running on a v3.x boot cd, but %s " \
                  "appears to be blank." % V3X_BOOTCD_SERVER_FILE

        cacert_file= V3X_BOOTCD_SERVER_CACERT

    else:
        raise BootManagerException, "Unknown boot cd version."

    if not os.access(cacert_file, os.R_OK):
        raise BootManagerException, \
              "Could not find the certificate for the " \
              "specified boot server (at %s)" % cacert_file

    # tell the log instance about the boot server so it knows
    # where to upload the logs
    try:
        log.SetUploadServer( self.VARS['MA_BOOT_SERVER'] )
    except KeyError, e:
        log.LogEntry( "configuration does not contain boot server name." )
        return


    # now that we have the boot server name and the location of its certificate,
    # write out /etc/planetlab/primary_ma with this info.
    try:
        primary_ma_file= file("/etc/planetlab/primary_ma","w")
        primary_ma_file.write( "MA_NAME=\"Unknown\"\n" )
        primary_ma_file.write( "MA_BOOT_SERVER=\"%s\"\n" % boot_server )
        primary_ma_file.write( "MA_BOOT_SERVER_CACERT=\"%s\"\n" % cacert_file )
        primary_ma_file.close()
        primary_ma_file= None
    except IOError:
        raise BootManagerException, "Unable to write out /etc/planetlab/primary_ma"
    
    vars['MA_BOOT_SERVER']= boot_server
    vars['MA_BOOT_SERVER_CACRET']= cacert_file

    self.Message( "Using boot server %s with certificate" %
                  (boot_server,cacert_file) )

    
    log.write( "Opening connection to API server\n" )
    api_server_url= "https://%s/PLCAPI/" % vars['MA_BOOT_SERVER']
    api_inst= xmlrpclib.Server( api_server_url, verbose=0 )
    vars['API_SERVER_INST']= api_inst

    
    # old cds need extra modules loaded for compaq smart array
    if BOOT_CD_VERSION[0] == 2:

        has_smartarray= utils.sysexec_noerr(
            'lspci | egrep "0e11:b178|0e11:4070|0e11:4080|0e11:4082|0e11:4083"')
        
        if has_smartarray:
            log.write( "Loading support for Compaq smart array\n" )
            utils.sysexec_noerr( "modprobe cciss", log )
            _create_cciss_dev_entries()
            

        has_fusion= utils.sysexec_noerr('lspci | egrep "1000:0030"')
        
        if has_fusion:
            log.write( "Loading support for Fusion MPT SCSI controllers\n" )
            utils.sysexec_noerr( "modprobe mptscsih", log )

    # for anything that needs to know we are running under the boot cd and
    # not the runtime os
    os.environ['PL_BOOTCD']= "1"
        
    return 1



def __check_boot_version( vars, log ):
    """
    identify which version of the boot os we are running on, and whether
    or not we can run at all on the given version. later, this will be
    used to identify extra packages to download to enable the boot manager
    to run on any supported version.

    2.x cds have the version file in /usr/bootme/ID, which looked like:
    'PlanetLab BootCD v2.0.3'

    3.x cds have the version file in /pl_version, which lookes like:
    'PlanetLab BootCD 3.0-beta0.3'

    All current known version strings that we support:
    PlanetLab BootCD 3.0
    PlanetLab BootCD 3.0-beta0.1
    PlanetLab BootCD 3.0-beta0.3
    PlanetLab BootCD v2.0
    PlanetLab BootCD v2.0.1
    PlanetLab BootCD v2.0.2
    PlanetLab BootCD v2.0.3

    Returns 1 if the boot os version is identified and will work
    to run the boot manager. Two class variables are set:
    BOOT_OS_MAJOR_VERSION
    BOOT_OS_MINOR_VERSION
    version strings with three parts parts to the version ignore the
    middle number (so 2.0.3 is major 2, minor 3)

    Returns 0 if the boot os is insufficient to run the boot manager
    """

    try:
        # check for a 3.x version first
        version_file= file(BOOT_VERSION_3X_FILE,'r')
        full_version= string.strip(version_file.read())
        version_file.close()

        version_parts= string.split(full_version)
        version= version_parts[-1]

        version_numbers= string.split(version,".")
        if len(version_numbers) == 2:
            BOOT_OS_MAJOR_VERSION= int(version_numbers[0])
            BOOT_OS_MINOR_VERSION= int(version_numbers[1])
        else:
            # for 3.x cds, if there are more than two parts
            # separated by a ., its one of the beta cds.
            # hardcode as a 3.0 cd
            BOOT_OS_MAJOR_VERSION= 3
            BOOT_OS_MINOR_VERSION= 0

        vars['BOOT_CD_VERSION']= (BOOT_OS_MAJOR_VERSION,BOOT_OS_MINOR_VERSION)
        
        if (BOOT_OS_MAJOR_VERSION,BOOT_OS_MINOR_VERSION) >= \
               MINIMUM_BOOT_VERSION:
            return 1

    except IOError, e:
        pass
    except IndexError, e:
        pass
    except TypeError, e:
        pass


    try:
        # check for a 2.x version first
        version_file= file(BOOT_VERSION_2X_FILE,'r')
        full_version= string.strip(version_file.read())
        version_file.close()

        version_parts= string.split(full_version)
        version= version_parts[-1]
        if version[0] == 'v':
            version= version[1:]

        version_numbers= string.split(version,".")
        if len(version_numbers) == 2:
            BOOT_OS_MAJOR_VERSION= int(version_numbers[0])
            BOOT_OS_MINOR_VERSION= int(version_numbers[1])
        else:
            BOOT_OS_MAJOR_VERSION= int(version_numbers[0])
            BOOT_OS_MINOR_VERSION= int(version_numbers[2])

        vars['BOOT_CD_VERSION']= (BOOT_OS_MAJOR_VERSION,BOOT_OS_MINOR_VERSION)

        if (BOOT_OS_MAJOR_VERSION,BOOT_OS_MINOR_VERSION) >= \
           MINIMUM_BOOT_VERSION:
            return 1

    except IOError, e:
        pass
    except IndexError, e:
        pass
    except TypeError, e:
        pass


    return 0



def _create_cciss_dev_entries():
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0 b 104 0" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p1 b 104 1" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p2 b 104 2" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p3 b 104 3" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p4 b 104 4" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p5 b 104 5" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p6 b 104 6" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p7 b 104 7" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p8 b 104 8" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p9 b 104 9" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p10 b 104 10" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p11 b 104 11" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p12 b 104 12" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p13 b 104 13" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p14 b 104 14" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d0p15 b 104 15" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1 b 104 16" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p1 b 104 17" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p2 b 104 18" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p3 b 104 19" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p4 b 104 20" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p5 b 104 21" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p6 b 104 22" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p7 b 104 23" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p8 b 104 24" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p9 b 104 25" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p10 b 104 26" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p11 b 104 27" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p12 b 104 28" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p13 b 104 29" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p14 b 104 30" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d1p15 b 104 31" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2 b 104 32" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p1 b 104 33" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p2 b 104 34" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p3 b 104 35" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p4 b 104 36" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p5 b 104 37" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p6 b 104 38" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p7 b 104 39" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p8 b 104 40" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p9 b 104 41" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p10 b 104 42" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p11 b 104 43" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p12 b 104 44" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p13 b 104 45" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p14 b 104 46" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d2p15 b 104 47" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3 b 104 48" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p1 b 104 49" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p2 b 104 50" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p3 b 104 51" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p4 b 104 52" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p5 b 104 53" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p6 b 104 54" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p7 b 104 55" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p8 b 104 56" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p9 b 104 57" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p10 b 104 58" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p11 b 104 59" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p12 b 104 60" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p13 b 104 61" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p14 b 104 62" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d3p15 b 104 63" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4 b 104 64" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p1 b 104 65" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p2 b 104 66" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p3 b 104 67" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p4 b 104 68" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p5 b 104 69" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p6 b 104 70" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p7 b 104 71" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p8 b 104 72" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p9 b 104 73" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p10 b 104 74" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p11 b 104 75" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p12 b 104 76" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p13 b 104 77" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p14 b 104 78" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d4p15 b 104 79" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5 b 104 80" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p1 b 104 81" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p2 b 104 82" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p3 b 104 83" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p4 b 104 84" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p5 b 104 85" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p6 b 104 86" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p7 b 104 87" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p8 b 104 88" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p9 b 104 89" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p10 b 104 90" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p11 b 104 91" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p12 b 104 92" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p13 b 104 93" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p14 b 104 94" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d5p15 b 104 95" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6 b 104 96" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p1 b 104 97" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p2 b 104 98" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p3 b 104 99" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p4 b 104 100" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p5 b 104 101" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p6 b 104 102" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p7 b 104 103" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p8 b 104 104" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p9 b 104 105" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p10 b 104 106" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p11 b 104 107" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p12 b 104 108" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p13 b 104 109" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p14 b 104 110" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d6p15 b 104 111" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7 b 104 112" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p1 b 104 113" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p2 b 104 114" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p3 b 104 115" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p4 b 104 116" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p5 b 104 117" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p6 b 104 118" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p7 b 104 119" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p8 b 104 120" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p9 b 104 121" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p10 b 104 122" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p11 b 104 123" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p12 b 104 124" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p13 b 104 125" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p14 b 104 126" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d7p15 b 104 127" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8 b 104 128" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p1 b 104 129" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p2 b 104 130" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p3 b 104 131" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p4 b 104 132" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p5 b 104 133" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p6 b 104 134" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p7 b 104 135" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p8 b 104 136" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p9 b 104 137" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p10 b 104 138" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p11 b 104 139" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p12 b 104 140" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p13 b 104 141" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p14 b 104 142" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d8p15 b 104 143" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9 b 104 144" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p1 b 104 145" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p2 b 104 146" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p3 b 104 147" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p4 b 104 148" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p5 b 104 149" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p6 b 104 150" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p7 b 104 151" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p8 b 104 152" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p9 b 104 153" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p10 b 104 154" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p11 b 104 155" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p12 b 104 156" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p13 b 104 157" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p14 b 104 158" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d9p15 b 104 159" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10 b 104 160" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p1 b 104 161" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p2 b 104 162" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p3 b 104 163" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p4 b 104 164" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p5 b 104 165" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p6 b 104 166" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p7 b 104 167" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p8 b 104 168" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p9 b 104 169" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p10 b 104 170" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p11 b 104 171" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p12 b 104 172" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p13 b 104 173" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p14 b 104 174" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d10p15 b 104 175" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11 b 104 176" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p1 b 104 177" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p2 b 104 178" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p3 b 104 179" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p4 b 104 180" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p5 b 104 181" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p6 b 104 182" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p7 b 104 183" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p8 b 104 184" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p9 b 104 185" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p10 b 104 186" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p11 b 104 187" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p12 b 104 188" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p13 b 104 189" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p14 b 104 190" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d11p15 b 104 191" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12 b 104 192" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p1 b 104 193" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p2 b 104 194" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p3 b 104 195" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p4 b 104 196" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p5 b 104 197" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p6 b 104 198" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p7 b 104 199" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p8 b 104 200" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p9 b 104 201" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p10 b 104 202" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p11 b 104 203" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p12 b 104 204" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p13 b 104 205" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p14 b 104 206" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d12p15 b 104 207" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13 b 104 208" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p1 b 104 209" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p2 b 104 210" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p3 b 104 211" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p4 b 104 212" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p5 b 104 213" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p6 b 104 214" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p7 b 104 215" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p8 b 104 216" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p9 b 104 217" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p10 b 104 218" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p11 b 104 219" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p12 b 104 220" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p13 b 104 221" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p14 b 104 222" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d13p15 b 104 223" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14 b 104 224" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p1 b 104 225" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p2 b 104 226" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p3 b 104 227" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p4 b 104 228" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p5 b 104 229" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p6 b 104 230" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p7 b 104 231" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p8 b 104 232" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p9 b 104 233" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p10 b 104 234" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p11 b 104 235" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p12 b 104 236" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p13 b 104 237" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p14 b 104 238" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d14p15 b 104 239" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15 b 104 240" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p1 b 104 241" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p2 b 104 242" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p3 b 104 243" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p4 b 104 244" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p5 b 104 245" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p6 b 104 246" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p7 b 104 247" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p8 b 104 248" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p9 b 104 249" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p10 b 104 250" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p11 b 104 251" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p12 b 104 252" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p13 b 104 253" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p14 b 104 254" )
    utils.sysexec_noerr( "mknod /dev/cciss/c0d15p15 b 104 255" )


    
