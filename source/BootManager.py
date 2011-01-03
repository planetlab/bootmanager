#!/usr/bin/python -u
#
# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.

import string
import sys, os, traceback
import time
import gzip

from steps import *
from Exceptions import *
import notify_messages
import BootServerRequest
import utils

# all output is written to this file
BM_NODE_LOG= "/tmp/bm.log"
VARS_FILE = "configuration"

# the new contents of PATH when the boot manager is running
BIN_PATH= ('/usr/local/bin',
           '/usr/local/sbin',
           '/usr/bin',
           '/usr/sbin',
           '/bin',
           '/sbin')

def read_configuration_file(filename):
    # read in and store all variables in VARS_FILE into each line
    # is in the format name=val (any whitespace around the = is
    # removed. everything after the = to the end of the line is
    # the value
    vars = {}
    vars_file= file(filename,'r')
    validConfFile = True
    for line in vars_file:
        # if its a comment or a whitespace line, ignore
        if line[:1] == "#" or string.strip(line) == "":
            continue

        parts= string.split(line,"=")
        if len(parts) != 2:
            validConfFile = False
            raise Exception( "Invalid line in vars file: %s" % line )

        name= string.strip(parts[0])
        value= string.strip(parts[1])
        value= value.replace("'", "")   # remove quotes
        value= value.replace('"', "")   # remove quotes
        vars[name]= value

    vars_file.close()
    if not validConfFile:
        raise Exception( "Unable to read configuration vars." )

    # find out which directory we are running it, and set a variable
    # for that. future steps may need to get files out of the bootmanager
    # directory
    current_dir= os.getcwd()
    vars['BM_SOURCE_DIR']= current_dir

    return vars

##############################
class log:

    format="%H:%M:%S(%Z) "

    def __init__( self, OutputFilePath= None ):
        try:
            self.OutputFile= open( OutputFilePath, "w")
            self.OutputFilePath= OutputFilePath
        except:
            print( "bootmanager log : Unable to open output file %r, continuing"%OutputFilePath )
            self.OutputFile= None

        self.VARS = None
        try:
            vars = read_configuration_file(VARS_FILE)
            self.VARS = vars
        except Exception, e:
            self.LogEntry( str(e) )
            return
    
    def LogEntry( self, str, inc_newline= 1, display_screen= 1 ):
        now=time.strftime(log.format, time.localtime())
        if self.OutputFile:
            self.OutputFile.write( now+str )
        if display_screen:
            sys.stdout.write( now+str )
            
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
    
    # bm log uploading is available back again, as of nodeconfig-5.0-2
    def Upload( self, extra_file=None ):
        """
        upload the contents of the log to the server
        """
        if self.OutputFile is not None:
            self.OutputFile.flush()

            self.LogEntry( "Uploading logs to %s" % self.VARS['UPLOAD_LOG_SCRIPT'] )
            
            self.OutputFile.close()
            self.OutputFile= None

            hostname= self.VARS['INTERFACE_SETTINGS']['hostname'] + "." + \
                      self.VARS['INTERFACE_SETTINGS']['domainname']
            bs_request = BootServerRequest.BootServerRequest(self.VARS)
            try:
                # this was working until f10
                bs_request.MakeRequest(PartialPath = self.VARS['UPLOAD_LOG_SCRIPT'],
                                       GetVars = None, PostVars = None,
                                       DoSSL = True, DoCertCheck = True,
                                       FormData = ["log=@" + self.OutputFilePath,
                                                   "hostname=" + hostname, 
                                                   "type=bm.log"])
            except:
                # new pycurl
                import pycurl
                bs_request.MakeRequest(PartialPath = self.VARS['UPLOAD_LOG_SCRIPT'],
                                       GetVars = None, PostVars = None,
                                       DoSSL = True, DoCertCheck = True,
                                       FormData = [('log',(pycurl.FORM_FILE, self.OutputFilePath)),
                                                   ("hostname",hostname),
                                                   ("type","bm.log")])
        if extra_file is not None:
            # NOTE: for code-reuse, evoke the bash function 'upload_logs'; 
            # by adding --login, bash reads .bash_profile before execution.
            # Also, never fail, since this is an optional feature.
            utils.sysexec_noerr( """bash --login -c "upload_logs %s" """ % extra_file, self)


##############################
class BootManager:

    # file containing initial variables/constants

    # the set of valid node run states
    NodeRunStates = {'reinstall':None,
                     'boot':None,
                     'safeboot':None,
                     'disabled':None,
                     }
    
    def __init__(self, log, forceState):
        # override machine's current state from the command line
        self.forceState = forceState

        # the main logging point
        self.LOG= log

        # set to 1 if we can run after initialization
        self.CAN_RUN = 0

        if log.VARS:
            # this contains a set of information used and updated by each step
            self.VARS= log.VARS
        else:
            return
             
        # not sure what the current PATH is set to, replace it with what
        # we know will work with all the boot cds
        os.environ['PATH']= string.join(BIN_PATH,":")

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

        def _nodeNotInstalled(message='MSG_NODE_NOT_INSTALLED'):
            # called by the _xxxState() functions below upon failure
            self.VARS['RUN_LEVEL']= 'failboot'
            notify = getattr(notify_messages, message)
            self.VARS['STATE_CHANGE_NOTIFY']= 1
            self.VARS['STATE_CHANGE_NOTIFY_MESSAGE']= notify
            raise BootManagerException, notify

        def _bootRun():
            # implements the boot logic, which consists of first
            # double checking that the node was properly installed,
            # checking whether someone added or changed disks, and
            # then finally chain boots.

            # starting the fallback/debug ssh daemon for safety:
            # if the node install somehow hangs, or if it simply takes ages, 
            # we can still enter and investigate
            try:
                StartDebug.Run(self.VARS, self.LOG, last_resort = False)
            except:
                pass

            InstallInit.Run( self.VARS, self.LOG )                    
            ret = ValidateNodeInstall.Run( self.VARS, self.LOG )
            if ret == 1:
                WriteModprobeConfig.Run( self.VARS, self.LOG )
                WriteNetworkConfig.Run( self.VARS, self.LOG )
                CheckForNewDisks.Run( self.VARS, self.LOG )
                SendHardwareConfigToPLC.Run( self.VARS, self.LOG )
                ChainBootNode.Run( self.VARS, self.LOG )
            elif ret == -1:
                _nodeNotInstalled('MSG_NODE_FILESYSTEM_CORRUPT')
            elif ret == -2:
                _nodeNotInstalled('MSG_NODE_MOUNT_FAILED')
            elif ret == -3:
                _nodeNotInstalled('MSG_NODE_MISSING_KERNEL')
            else:
                _nodeNotInstalled()

        def _reinstallRun():

            # starting the fallback/debug ssh daemon for safety:
            # if the node install somehow hangs, or if it simply takes ages, 
            # we can still enter and investigate
            try:
                StartDebug.Run(self.VARS, self.LOG, last_resort = False)
            except:
                pass

            # implements the reinstall logic, which will check whether
            # the min. hardware requirements are met, install the
            # software, and upon correct installation will switch too
            # 'boot' state and chainboot into the production system
            if not CheckHardwareRequirements.Run( self.VARS, self.LOG ):
                self.VARS['RUN_LEVEL']= 'failboot'
                raise BootManagerException, "Hardware requirements not met."

            # runinstaller
            InstallInit.Run( self.VARS, self.LOG )                    
            InstallPartitionDisks.Run( self.VARS, self.LOG )            
            InstallBootstrapFS.Run( self.VARS, self.LOG )            
            InstallWriteConfig.Run( self.VARS, self.LOG )
            InstallUninitHardware.Run( self.VARS, self.LOG )
            self.VARS['BOOT_STATE']= 'boot'
            self.VARS['STATE_CHANGE_NOTIFY']= 1
            self.VARS['STATE_CHANGE_NOTIFY_MESSAGE']= \
                 notify_messages.MSG_INSTALL_FINISHED
            UpdateBootStateWithPLC.Run( self.VARS, self.LOG )
            _bootRun()
            
        def _installRun():
            # implements the new install logic, which will first check
            # with the user whether it is ok to install on this
            # machine, switch to 'reinstall' state and then invoke the reinstall
            # logic.  See reinstallState logic comments for further
            # details.
            if not ConfirmInstallWithUser.Run( self.VARS, self.LOG ):
                return 0
            self.VARS['BOOT_STATE']= 'reinstall'
            UpdateRunLevelWithPLC.Run( self.VARS, self.LOG )
            _reinstallRun()

        def _debugRun(state='failboot'):
            # implements debug logic, which starts the sshd and just waits around
            self.VARS['RUN_LEVEL']=state
            UpdateRunLevelWithPLC.Run( self.VARS, self.LOG )
            StartDebug.Run( self.VARS, self.LOG )
            # fsck/mount fs if present, and ignore return value if it's not.
            ValidateNodeInstall.Run( self.VARS, self.LOG )

        def _badstateRun():
            # should never happen; log event
            self.LOG.write( "\nInvalid BOOT_STATE = %s\n" % self.VARS['BOOT_STATE'])
            _debugRun()

        # setup state -> function hash table
        BootManager.NodeRunStates['reinstall']  = _reinstallRun
        BootManager.NodeRunStates['boot']       = _bootRun
        BootManager.NodeRunStates['safeboot']   = lambda : _debugRun('safeboot')
        BootManager.NodeRunStates['disabled']   = lambda : _debugRun('disabled')

        success = 0
        try:
            InitializeBootManager.Run( self.VARS, self.LOG )
            ReadNodeConfiguration.Run( self.VARS, self.LOG )
            AuthenticateWithPLC.Run( self.VARS, self.LOG )
            StartRunlevelAgent.Run( self.VARS, self.LOG )
            GetAndUpdateNodeDetails.Run( self.VARS, self.LOG )

            # override machine's current state from the command line
            if self.forceState is not None:
                self.VARS['BOOT_STATE']= self.forceState
                UpdateBootStateWithPLC.Run( self.VARS, self.LOG )
                UpdateRunLevelWithPLC.Run( self.VARS, self.LOG )

            stateRun = BootManager.NodeRunStates.get(self.VARS['BOOT_STATE'],_badstateRun)
            stateRun()
            success = 1

        except KeyError, e:
            self.LOG.write( "\n\nKeyError while running: %s\n" % str(e) )
        except BootManagerException, e:
            self.LOG.write( "\n\nException while running: %s\n" % str(e) )
        except BootManagerAuthenticationException, e:
            self.LOG.write( "\n\nFailed to Authenticate Node: %s\n" % str(e) )
            # sets /tmp/CANCEL_BOOT flag
            StartDebug.Run(self.VARS, self.LOG )
            # Return immediately b/c any other calls to API will fail
            return success
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

    import utils
    utils.prompt_for_breakpoint_mode()

    utils.breakpoint ("Entering BootManager::main")
    
    # set to 1 if error occurred
    error= 0
    
    # all output goes through this class so we can save it and post
    # the data back to PlanetLab central
    LOG= log( BM_NODE_LOG )

    # NOTE: assume CWD is BM's source directory, but never fail
    utils.sysexec_noerr("./setup_bash_history_scripts.sh", LOG)

    LOG.LogEntry( "BootManager started at: %s" % \
                  time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime()) )

    try:
        forceState = None
        if len(argv) == 2:
            fState = argv[1]
            if BootManager.NodeRunStates.has_key(fState):
                forceState = fState
            else:
                LOG.LogEntry("FATAL: cannot force node run state to=%s" % fState)
                error = 1
    except:
        traceback.print_exc(file=LOG.OutputFile)
        traceback.print_exc()
        
    if error:
        LOG.LogEntry( "BootManager finished at: %s" % \
                      time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime()) )
        LOG.Upload()
        return error

    try:
        bm= BootManager(LOG,forceState)
        if bm.CAN_RUN == 0:
            LOG.LogEntry( "Unable to initialize BootManager." )
        else:
            LOG.LogEntry( "Running version %s of BootManager." % bm.VARS['VERSION'] )
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
                  time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime()) )
    LOG.Upload()

    return error

    
if __name__ == "__main__":
    error = main(sys.argv)
    sys.exit(error)
