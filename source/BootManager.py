#!/usr/bin/python2 -u

# ------------------------------------------------------------------------
# THIS file used to be named alpina.py, from the node installer. Since then
# the installer has been expanded to include all the functions of the boot
# manager as well, hence the new name for this file.
# ------------------------------------------------------------------------

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


import string
import sys, os, traceback
from time import gmtime, strftime
from gzip import GzipFile

from steps import *
from Exceptions import *
import notify_messages



# all output is written to this file
LOG_FILE= "/tmp/bm.log"
CURL_PATH= "curl"
UPLOAD_LOG_URL = "http://boot.planet-lab.org/alpina-logs/upload.php"

# the new contents of PATH when the boot manager is running
BIN_PATH= ('/usr/local/bin',
           '/usr/local/sbin',
           '/bin',
           '/sbin',
           '/usr/bin',
           '/usr/sbin',
           '/usr/local/planetlab/bin')
           


class log:

    def __init__( self, OutputFilePath= None ):
        if OutputFilePath:
            try:
                self.OutputFilePath= OutputFilePath
                self.OutputFile= GzipFile( OutputFilePath, "w", 9 )
            except:
                print( "Unable to open output file for log, continuing" )
                self.OutputFile= None

    
    def LogEntry( self, str, inc_newline= 1, display_screen= 1 ):
        if self.OutputFile:
            self.OutputFile.write( str )
        if display_screen:
            sys.stdout.write( str )
            
        if inc_newline:
            if display_screen:
                sys.stdout.write( "\n" )
            if self.OutputFile:
                self.OutputFile.write( "\n" )

        if self.OutputFile:
            self.OutputFile.flush()

            

    def write( self, str ):
        """
        make log behave like a writable file object (for traceback
        prints)
        """
        self.LogEntry( str, 0, 1 )


    
    def Upload( self ):
        """
        upload the contents of the log to the server
        """

        if self.OutputFile is not None:
            self.LogEntry( "Uploading logs to %s" % UPLOAD_LOG_URL )
            
            self.OutputFile.close()
            self.OutputFile= None
            
            curl_cmd= "%s -s --connect-timeout 60 --max-time 600 " \
                      "--form log=@%s %s" % \
                      (CURL_PATH, self.OutputFilePath, UPLOAD_LOG_URL)
            os.system( curl_cmd )
        
    

        


class BootManager:

    # file containing initial variables/constants
    VARS_FILE = "configuration"

    
    def __init__(self, log):
        # this contains a set of information used and updated
        # by each step
        self.VARS= {}

        # the main logging point
        self.LOG= log

        # set to 1 if we can run after initialization
        self.CAN_RUN = 0
             
        if not self.ReadBMConf():
            self.LOG.LogEntry( "Unable to read configuration vars." )
            return

        # find out which directory we are running it, and set a variable
        # for that. future steps may need to get files out of the bootmanager
        # directory
        current_dir= os.getcwd()
        self.VARS['BM_SOURCE_DIR']= current_dir

        # not sure what the current PATH is set to, replace it with what
        # we know will work with all the boot cds
        os.environ['PATH']= string.join(BIN_PATH,":")
                   
        self.CAN_RUN= 1
        



    def ReadBMConf(self):
        """
        read in and store all variables in VARS_FILE into
        self.VARS
        
        each line is in the format name=val (any whitespace around
        the = is removed. everything after the = to the end of
        the line is the value
        """
        
        vars_file= file(self.VARS_FILE,'r')
        for line in vars_file:
            # if its a comment or a whitespace line, ignore
            if line[:1] == "#" or string.strip(line) == "":
                continue

            parts= string.split(line,"=")
            if len(parts) != 2:
                self.LOG.LogEntry( "Invalid line in vars file: %s" % line )
                return 0

            name= string.strip(parts[0])
            value= string.strip(parts[1])

            self.VARS[name]= value

        return 1
    

    def Run(self):
        """
        core boot manager logic.

        the way errors are handled is as such: if any particular step
        cannot continue or unexpectibly fails, an exception is thrown.
        in this case, the boot manager cannot continue running.

        these step functions can also return a 0/1 depending on whether
        or not it succeeded. In the case of steps like ConfirmInstallWithUser,
        a 0 is returned and no exception is thrown if the user chose not
        to confirm the install. The same goes with the CheckHardwareRequirements.
        If requriements not met, but tests were succesfull, return 0.

        for steps that run within the installer, they are expected to either
        complete succesfully and return 1, or throw an execption.

        For exact return values and expected operations, see the comments
        at the top of each of the invididual step functions.
        """
        
        try:
            InitializeBootManager.Run( self.VARS, self.LOG )
            ReadNodeConfiguration.Run( self.VARS, self.LOG )
            AuthenticateWithPLC.Run( self.VARS, self.LOG )
            GetAndUpdateNodeDetails.Run( self.VARS, self.LOG )
            
            if self.VARS['BOOT_STATE'] == 'new' or \
                   self.VARS['BOOT_STATE'] == 'inst':
                if not ConfirmInstallWithUser.Run( self.VARS, self.LOG ):
                    return 0
                
                self.VARS['BOOT_STATE']= 'rins'
                UpdateBootStateWithPLC.Run( self.VARS, self.LOG )
            
                if not CheckHardwareRequirements.Run( self.VARS, self.LOG ):
                    self.VARS['BOOT_STATE']= 'dbg'
                    UpdateBootStateWithPLC.Run( self.VARS, self.LOG )
                    raise BootManagerException, "Hardware requirements not met."

                self.RunInstaller()

                if ValidateNodeInstall.Run( self.VARS, self.LOG ):
                    SendHardwareConfigToPLC.Run( self.VARS, self.LOG )
                    ChainBootNode.Run( self.VARS, self.LOG )
                else:
                    self.VARS['BOOT_STATE']= 'dbg'
                    self.VARS['STATE_CHANGE_NOTIFY']= 1
                    self.VARS['STATE_CHANGE_NOTIFY_MESSAGE']= \
                              notify_messages.MSG_NODE_NOT_INSTALLED
                    UpdateBootStateWithPLC.Run( self.VARS, self.LOG )
                    

            elif self.VARS['BOOT_STATE'] == 'rins':
                if not CheckHardwareRequirements.Run( self.VARS, self.LOG ):
                    self.VARS['BOOT_STATE']= 'dbg'
                    UpdateBootStateWithPLC.Run( self.VARS, self.LOG )
                    raise BootManagerException, "Hardware requirements not met."
                
                self.RunInstaller()

                if ValidateNodeInstall.Run( self.VARS, self.LOG ):
                    SendHardwareConfigToPLC.Run( self.VARS, self.LOG )
                    ChainBootNode.Run( self.VARS, self.LOG )
                else:
                    self.VARS['BOOT_STATE']= 'dbg'
                    self.VARS['STATE_CHANGE_NOTIFY']= 1
                    self.VARS['STATE_CHANGE_NOTIFY_MESSAGE']= \
                              notify_messages.MSG_NODE_NOT_INSTALLED
                    UpdateBootStateWithPLC.Run( self.VARS, self.LOG )

            elif self.VARS['BOOT_STATE'] == 'boot':
                if ValidateNodeInstall.Run( self.VARS, self.LOG ):
                    UpdateNodeConfiguration.Run( self.VARS, self.LOG )
                    CheckForNewDisks.Run( self.VARS, self.LOG )
                    SendHardwareConfigToPLC.Run( self.VARS, self.LOG )
                    ChainBootNode.Run( self.VARS, self.LOG )
                else:
                    self.VARS['BOOT_STATE']= 'dbg'
                    self.VARS['STATE_CHANGE_NOTIFY']= 1
                    self.VARS['STATE_CHANGE_NOTIFY_MESSAGE']= \
                              notify_messages.MSG_NODE_NOT_INSTALLED
                    UpdateBootStateWithPLC.Run( self.VARS, self.LOG )
                    
            elif self.VARS['BOOT_STATE'] == 'dbg':
                StartDebug.Run( self.VARS, self.LOG )

        except KeyError, e:
            self.LOG.write( "\n\nKeyError while running: %s\n" % str(e) )
        except BootManagerException, e:
            self.LOG.write( "\n\nException while running: %s\n" % str(e) )
        
        return 1
            

            
    def RunInstaller(self):
        """
        since the installer can be invoked at more than one place
        in the boot manager logic, seperate the steps necessary
        to do it here
        """
        
        InstallInit.Run( self.VARS, self.LOG )                    
        InstallPartitionDisks.Run( self.VARS, self.LOG )            
        InstallBootstrapRPM.Run( self.VARS, self.LOG )            
        InstallBase.Run( self.VARS, self.LOG )            
        InstallWriteConfig.Run( self.VARS, self.LOG )
        InstallBuildVServer.Run( self.VARS, self.LOG )
        InstallNodeInit.Run( self.VARS, self.LOG )
        InstallUninitHardware.Run( self.VARS, self.LOG )
        
        self.VARS['BOOT_STATE']= 'boot'
        self.VARS['STATE_CHANGE_NOTIFY']= 1
        self.VARS['STATE_CHANGE_NOTIFY_MESSAGE']= \
                                       notify_messages.MSG_INSTALL_FINISHED
        UpdateBootStateWithPLC.Run( self.VARS, self.LOG )

        SendHardwareConfigToPLC.Run( self.VARS, self.LOG )

    
    
if __name__ == "__main__":

    # set to 0 if no error occurred
    error= 1
    
    # all output goes through this class so we can save it and post
    # the data back to PlanetLab central
    LOG= log( LOG_FILE )

    LOG.LogEntry( "BootManager started at: %s" % \
                  strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()) )

    try:
        bm= BootManager(LOG)
        if bm.CAN_RUN == 0:
            LOG.LogEntry( "Unable to initialize BootManager." )
        else:
            LOG.LogEntry( "Running version %s of BootManager." %
                          bm.VARS['VERSION'] )
            success= bm.Run()
            if success:
                LOG.LogEntry( "\nDone!" );
            else:
                LOG.LogEntry( "\nError occurred!" );

    except:
        traceback.print_exc(file=LOG.OutputFile)
        traceback.print_exc()

    LOG.LogEntry( "BootManager finished at: %s" % \
                  strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()) )

    LOG.Upload()
    
    sys.exit(error)
