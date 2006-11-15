#!/usr/bin/python2 -u

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.

import string
import sys, os, traceback
from time import gmtime, strftime
from gzip import GzipFile

from steps import *
from Exceptions import *
import notify_messages
import BootServerRequest

# all output is written to this file
LOG_FILE= "/tmp/bm.log"
UPLOAD_LOG_PATH = "/alpina-logs/upload.php"

# the new contents of PATH when the boot manager is running
BIN_PATH= ('/usr/local/bin',
           '/usr/local/sbin',
           '/bin',
           '/sbin',
           '/usr/bin',
           '/usr/sbin',
           '/usr/local/planetlab/bin')
           

# the set of valid node run states
NodeRunStates = {}

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
            self.LogEntry( "Uploading logs to %s" % UPLOAD_LOG_PATH )
            
            self.OutputFile.close()
            self.OutputFile= None

            bs_request = BootServerRequest.BootServerRequest()
            bs_request.MakeRequest(PartialPath = UPLOAD_LOG_PATH,
                                   GetVars = None, PostVars = None,
                                   FormData = ["log=@" + self.OutputFilePath],
                                   DoSSL = True, DoCertCheck = True)
        
    

        


class BootManager:

    # file containing initial variables/constants
    VARS_FILE = "configuration"

    
    def __init__(self, log, forceState):
        # override machine's current state from the command line
        self.forceState = forceState

        # the main logging point
        self.LOG= log

        # set to 1 if we can run after initialization
        self.CAN_RUN = 0
             
        # read in and store all variables in VARS_FILE into each line
        # is in the format name=val (any whitespace around the = is
        # removed. everything after the = to the end of the line is
        # the value
        vars = {}
        vars_file= file(self.VARS_FILE,'r')
        validConfFile = True
        for line in vars_file:
            # if its a comment or a whitespace line, ignore
            if line[:1] == "#" or string.strip(line) == "":
                continue

            parts= string.split(line,"=")
            if len(parts) != 2:
                self.LOG.LogEntry( "Invalid line in vars file: %s" % line )
                validConfFile = False
                break

            name= string.strip(parts[0])
            value= string.strip(parts[1])
            vars[name]= value

        vars_file.close()
        if not validConfFile:
            self.LOG.LogEntry( "Unable to read configuration vars." )
            return

        # find out which directory we are running it, and set a variable
        # for that. future steps may need to get files out of the bootmanager
        # directory
        current_dir= os.getcwd()
        vars['BM_SOURCE_DIR']= current_dir

        # not sure what the current PATH is set to, replace it with what
        # we know will work with all the boot cds
        os.environ['PATH']= string.join(BIN_PATH,":")
                   
        # this contains a set of information used and updated
        # by each step
        self.VARS= vars

        self.CAN_RUN= 1

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

        def _nodeNotInstalled():
            # called by the _xxxState() functions below upon failure
            self.VARS['BOOT_STATE']= 'dbg'
            self.VARS['STATE_CHANGE_NOTIFY']= 1
            self.VARS['STATE_CHANGE_NOTIFY_MESSAGE']= \
                      notify_messages.MSG_NODE_NOT_INSTALLED
            raise BootManagerException, \
                  notify_messages.MSG_NODE_NOT_INSTALLED

        def _bootRun():
            # implements the boot logic, which consists of first
            # double checking that the node was properly installed,
            # checking whether someone added or changed disks, and
            # then finally chain boots.

            InstallInit.Run( self.VARS, self.LOG )                    
            if ValidateNodeInstall.Run( self.VARS, self.LOG ):
                WriteModprobeConfig.Run( self.VARS, self.LOG )
                MakeInitrd.Run( self.VARS, self.LOG )
                WriteNetworkConfig.Run( self.VARS, self.LOG )
                # the following step should be done by NM
                UpdateNodeConfiguration.Run( self.VARS, self.LOG )
                CheckForNewDisks.Run( self.VARS, self.LOG )
                SendHardwareConfigToPLC.Run( self.VARS, self.LOG )
                ChainBootNode.Run( self.VARS, self.LOG )
            else:
                _nodeNotInstalled()

        def _rinsRun():
            # implements the reinstall logic, which will check whether
            # the min. hardware requirements are met, install the
            # software, and upon correct installation will switch too
            # 'boot' state and chainboot into the production system
            if not CheckHardwareRequirements.Run( self.VARS, self.LOG ):
                self.VARS['BOOT_STATE']= 'dbg'
                raise BootManagerException, "Hardware requirements not met."

            # runinstaller
            InstallInit.Run( self.VARS, self.LOG )                    
            InstallPartitionDisks.Run( self.VARS, self.LOG )            
            InstallBootstrapRPM.Run( self.VARS, self.LOG )            
            InstallWriteConfig.Run( self.VARS, self.LOG )
            InstallBuildVServer.Run( self.VARS, self.LOG )
            InstallUninitHardware.Run( self.VARS, self.LOG )
            self.VARS['BOOT_STATE']= 'boot'
            self.VARS['STATE_CHANGE_NOTIFY']= 1
            self.VARS['STATE_CHANGE_NOTIFY_MESSAGE']= \
                 notify_messages.MSG_INSTALL_FINISHED
            UpdateBootStateWithPLC.Run( self.VARS, self.LOG )
            _bootRun()
            
        def _newRun():
            # implements the new install logic, which will first check
            # with the user whether it is ok to install on this
            # machine, switch to 'rins' state and then invoke the rins
            # logic.  See rinsState logic comments for further
            # details.
            if not ConfirmInstallWithUser.Run( self.VARS, self.LOG ):
                return 0
            self.VARS['BOOT_STATE']= 'rins'
            UpdateBootStateWithPLC.Run( self.VARS, self.LOG )
            _rinsRun()

        def _debugRun():
            # implements debug logic, which just starts the sshd
            # and just waits around
            self.VARS['BOOT_STATE']='dbg'
            UpdateBootStateWithPLC.Run( self.VARS, self.LOG )
            StartDebug.Run( self.VARS, self.LOG )

        def _badRun():
            # should never happen; log event
            self.LOG.write( "\nInvalid BOOT_STATE = %s\n" % self.VARS['BOOT_STATE'])
            _debugRun()

        global NodeRunStates
        # setup state -> function hash table
        NodeRunStates['new']  = _newRun
        NodeRunStates['inst'] = _newRun
        NodeRunStates['rins'] = _rinsRun
        NodeRunStates['boot'] = _bootRun
        NodeRunStates['dbg']  = _debugRun

        success = 0
        try:
            InitializeBootManager.Run( self.VARS, self.LOG )
            ReadNodeConfiguration.Run( self.VARS, self.LOG )
            AuthenticateWithPLC.Run( self.VARS, self.LOG )
            GetAndUpdateNodeDetails.Run( self.VARS, self.LOG )

            # override machine's current state from the command line
            if self.forceState is not None:
                self.VARS['BOOT_STATE']= self.forceState
                UpdateBootStateWithPLC.Run( self.VARS, self.LOG )

            stateRun = NodeRunStates.get(self.VARS['BOOT_STATE'],_badRun)
            stateRun()
            success = 1

        except KeyError, e:
            self.LOG.write( "\n\nKeyError while running: %s\n" % str(e) )
        except BootManagerException, e:
            self.LOG.write( "\n\nException while running: %s\n" % str(e) )
        except:
            self.LOG.write( "\n\nImplementation Error\n")
            traceback.print_exc(file=self.LOG.OutputFile)
            traceback.print_exc()

        if not success:
            try:
                _debugRun()
            except BootManagerException, e:
                self.LOG.write( "\n\nException while running: %s\n" % str(e) )
            except:
                self.LOG.write( "\n\nImplementation Error\n")
                traceback.print_exc(file=self.LOG.OutputFile)
                traceback.print_exc()

        return success
            
            
def main(argv):
    global NodeRunStates
    NodeRunStates = {'new':None,
                     'inst':None,
                     'rins':None,
                     'boot':None,
                     'dbg':None}

    # set to 1 if error occurred
    error= 0
    
    # all output goes through this class so we can save it and post
    # the data back to PlanetLab central
    LOG= log( LOG_FILE )

    LOG.LogEntry( "BootManager started at: %s" % \
                  strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()) )

    try:
        forceState = None
        if len(argv) == 2:
            fState = argv[1]
            if NodeRunStates.has_key(fState):
                forceState = fState
            else:
                LOG.LogEntry("FATAL: cannot force node run state to=%s" % fState)
                error = 1
    except:
        traceback.print_exc(file=LOG.OutputFile)
        traceback.print_exc()
        
    if error:
        LOG.LogEntry( "BootManager finished at: %s" % \
                      strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()) )
        LOG.Upload()
        return error

    try:
        bm= BootManager(LOG,forceState)
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
                error = 1
    except:
        traceback.print_exc(file=LOG.OutputFile)
        traceback.print_exc()

    LOG.LogEntry( "BootManager finished at: %s" % \
                  strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()) )
    LOG.Upload()

    return error

    
if __name__ == "__main__":
    error = main(sys.argv)
    sys.exit(error)
