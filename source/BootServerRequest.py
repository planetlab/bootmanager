#!/usr/bin/python2

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


import os, sys
import re
import string
import urllib
import tempfile

# try to load pycurl
try:
    import pycurl
    PYCURL_LOADED= 1
except:
    PYCURL_LOADED= 0


# if there is no cStringIO, fall back to the original
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO



class BootServerRequest:

    VERBOSE = 0

    # all possible places to check the cdrom mount point.
    # /mnt/cdrom is typically after the machine has come up,
    # and /usr is when the boot cd is running
    CDROM_MOUNT_PATH = ("/mnt/cdrom/","/usr/")

    # this is the server to contact if we don't have a bootcd
    DEFAULT_BOOT_SERVER = "boot.planet-lab.org"

    BOOTCD_VERSION_FILE = "bootme/ID"
    BOOTCD_SERVER_FILE = "bootme/BOOTSERVER"
    BOOTCD_SERVER_CERT_DIR = "bootme/cacert"
    CACERT_NAME = "cacert.pem"
    
    # location of file containing http/https proxy info, if needed
    PROXY_FILE = '/etc/planetlab/http_proxy'

    # location of curl executable, if pycurl isn't available
    # and the DownloadFile method is called (backup, only
    # really need for the boot cd environment where pycurl
    # doesn't exist
    CURL_CMD = 'curl'

    # in seconds, how maximum time allowed for connect
    DEFAULT_CURL_CONNECT_TIMEOUT = 30

    # in seconds, maximum time allowed for any transfer
    DEFAULT_CURL_MAX_TRANSFER_TIME = 3600

    CURL_SSL_VERSION = 3

    HTTP_SUCCESS = 200

    # proxy variables
    USE_PROXY = 0
    PROXY = 0

    # bootcd variables
    HAS_BOOTCD = 0
    BOOTCD_VERSION = ""
    BOOTSERVER_CERTS= {}

    def __init__(self, verbose=0):

        self.VERBOSE= verbose
            
        # see if we have a boot cd mounted by checking for the version file
        # if HAS_BOOTCD == 0 then either the machine doesn't have
        # a boot cd, or something else is mounted
        self.HAS_BOOTCD = 0

        for path in self.CDROM_MOUNT_PATH:
            self.Message( "Checking existance of boot cd on %s" % path )

            os.system("/bin/mount %s > /dev/null 2>&1" % path )
                
            version_file= path + self.BOOTCD_VERSION_FILE
            self.Message( "Looking for version file %s" % version_file )

            if os.access(version_file, os.R_OK) == 0:
                self.Message( "No boot cd found." );
            else:
                self.Message( "Found boot cd." )
                self.HAS_BOOTCD=1
                break


        if self.HAS_BOOTCD:

            # check the version of the boot cd, and locate the certs
            self.Message( "Getting boot cd version." )
        
            versionRegExp= re.compile(r"PlanetLab BootCD v(\S+)")
                
            bootcd_version_f= file(version_file,"r")
            line= string.strip(bootcd_version_f.readline())
            bootcd_version_f.close()
            
            match= versionRegExp.findall(line)
            if match:
                (self.BOOTCD_VERSION)= match[0]
            
            # right now, all the versions of the bootcd are supported,
            # so no need to check it
            
            # create a list of the servers we should
            # attempt to contact, and the certs for each
            server_list= path + self.BOOTCD_SERVER_FILE
            self.Message( "Getting list of servers off of cd from %s." %
                          server_list )
            
            bootservers_f= file(server_list,"r")
            bootservers= bootservers_f.readlines()
            bootservers_f.close()
            
            for bootserver in bootservers:
                bootserver = string.strip(bootserver)
                cacert_path= "%s/%s/%s/%s" % \
                             (path,self.BOOTCD_SERVER_CERT_DIR,
                              bootserver,self.CACERT_NAME)
                if os.access(cacert_path, os.R_OK):
                    self.BOOTSERVER_CERTS[bootserver]= cacert_path

            self.Message( "Set of servers to contact: %s" %
                          str(self.BOOTSERVER_CERTS) )
        else:
            self.Message( "Using default boot server address." )
            self.BOOTSERVER_CERTS[self.DEFAULT_BOOT_SERVER]= ""


    def CheckProxy( self ):
        # see if we have any proxy info from the machine
        self.USE_PROXY= 0
        self.Message( "Checking existance of proxy config file..." )
        
        if os.access(self.PROXY_FILE, os.R_OK) and \
               os.path.isfile(self.PROXY_FILE):
            self.PROXY= string.strip(file(self.PROXY_FILE,'r').readline())
            self.USE_PROXY= 1
            self.Message( "Using proxy %s." % self.PROXY )
        else:
            self.Message( "Not using any proxy." )



    def Message( self, Msg ):
        if( self.VERBOSE ):
            print( Msg )



    def Error( self, Msg ):
        sys.stderr.write( Msg + "\n" )



    def Warning( self, Msg ):
        self.Error(Msg)



    def MakeRequest( self, PartialPath, GetVars,
                     PostVars, DoSSL, DoCertCheck,
                     ConnectTimeout= DEFAULT_CURL_CONNECT_TIMEOUT,
                     MaxTransferTime= DEFAULT_CURL_MAX_TRANSFER_TIME,
                     FormData= None):

        if hasattr(tempfile, "NamedTemporaryFile"):
            buffer = tempfile.NamedTemporaryFile()
            buffer_name = buffer.name
        else:
            buffer_name = tempfile.mktemp("MakeRequest")
            buffer = open(buffer_name, "w+")

        ok = self.DownloadFile(PartialPath, GetVars, PostVars,
                               DoSSL, DoCertCheck, buffer_name,
                               ConnectTimeout,
                               MaxTransferTime,
                               FormData)

        # check the code, return the string only if it was successfull
        if ok:
            buffer.seek(0)
            return buffer.read()
        else:
            return None

    def DownloadFile(self, PartialPath, GetVars, PostVars,
                     DoSSL, DoCertCheck, DestFilePath,
                     ConnectTimeout= DEFAULT_CURL_CONNECT_TIMEOUT,
                     MaxTransferTime= DEFAULT_CURL_MAX_TRANSFER_TIME,
                     FormData= None):

        self.Message( "Attempting to retrieve %s" % PartialPath )

        # we can't do ssl and check the cert if we don't have a bootcd
        if DoSSL and DoCertCheck and not self.HAS_BOOTCD:
            self.Error( "No boot cd exists (needed to use -c and -s.\n" )
            return 0

        if DoSSL and not PYCURL_LOADED:
            self.Warning( "Using SSL without pycurl will by default " \
                          "check at least standard certs." )

        # ConnectTimeout has to be greater than 0
        if ConnectTimeout <= 0:
            self.Error( "Connect timeout must be greater than zero.\n" )
            return 0


        self.CheckProxy()

        dopostdata= 0

        # setup the post and get vars for the request
        if PostVars:
            dopostdata= 1
            postdata = urllib.urlencode(PostVars)
            self.Message( "Posting data:\n%s\n" % postdata )
            
        getstr= ""
        if GetVars:
            getstr= "?" + urllib.urlencode(GetVars)
            self.Message( "Get data:\n%s\n" % getstr )

        # now, attempt to make the request, starting at the first
        # server in the list
        
        for server in self.BOOTSERVER_CERTS:
            self.Message( "Contacting server %s." % server )
                        
            certpath = self.BOOTSERVER_CERTS[server]

            
            # output what we are going to be doing
            self.Message( "Connect timeout is %s seconds" % \
                          ConnectTimeout )

            self.Message( "Max transfer time is %s seconds" % \
                          MaxTransferTime )

            if DoSSL:
                url = "https://%s/%s%s" % (server,PartialPath,getstr)
                
                if DoCertCheck and PYCURL_LOADED:
                    self.Message( "Using SSL version %d and verifying peer." %
                             self.CURL_SSL_VERSION )
                else:
                    self.Message( "Using SSL version %d." %
                             self.CURL_SSL_VERSION )
            else:
                url = "http://%s/%s%s" % (server,PartialPath,getstr)
                
            self.Message( "URL: %s" % url )
            
            # setup a new pycurl instance, or a curl command line string
            # if we don't have pycurl
            
            if PYCURL_LOADED:
                curl= pycurl.Curl()

                # don't want curl sending any signals
                curl.setopt(pycurl.NOSIGNAL, 1)
            
                curl.setopt(pycurl.CONNECTTIMEOUT, ConnectTimeout)
                curl.setopt(pycurl.TIMEOUT, MaxTransferTime)

                # do not follow location when attempting to download a file
                curl.setopt(pycurl.FOLLOWLOCATION, 0)

                if self.USE_PROXY:
                    curl.setopt(pycurl.PROXY, self.PROXY )

                if DoSSL:
                    curl.setopt(pycurl.SSLVERSION, self.CURL_SSL_VERSION)
                
                    if DoCertCheck:
                        curl.setopt(pycurl.CAINFO, certpath)
                        curl.setopt(pycurl.SSL_VERIFYPEER, 2)
                        
                    else:
                        curl.setopt(pycurl.SSL_VERIFYPEER, 0)
                
                if dopostdata:
                    curl.setopt(pycurl.POSTFIELDS, postdata)

                # setup multipart/form-data upload
                if FormData:
                    curl.setopt(pycurl.HTTPPOST, FormData)

                curl.setopt(pycurl.URL, url)
            else:

                cmdline = "%s " \
                          "--connect-timeout %d " \
                          "--max-time %d " \
                          "--header Pragma: " \
                          "--output %s " \
                          "--fail " % \
                          (self.CURL_CMD, ConnectTimeout,
                           MaxTransferTime, DestFilePath)

                if dopostdata:
                    cmdline = cmdline + "--data '" + postdata + "' "

                if FormData:
                    cmdline = cmdline + "".join(["--form '" + field + "' " for field in FormData])

                if not self.VERBOSE:
                    cmdline = cmdline + "--silent "
                    
                if self.USE_PROXY:
                    cmdline = cmdline + "--proxy %s " % self.PROXY

                if DoSSL:
                    cmdline = cmdline + "--sslv%d " % self.CURL_SSL_VERSION

                    if DoCertCheck:
                        cmdline = cmdline + "--cacert %s " % certpath
                 
                cmdline = cmdline + url

                self.Message( "curl command: %s" % cmdline )
                
                
            if PYCURL_LOADED:
                try:
                    # setup the output file
                    outfile = open(DestFilePath,"wb")
                    
                    self.Message( "Opened output file %s" % DestFilePath )
                
                    curl.setopt(pycurl.WRITEDATA, outfile)
                
                    self.Message( "Fetching..." )
                    curl.perform()
                    self.Message( "Done." )
                
                    http_result= curl.getinfo(pycurl.HTTP_CODE)
                    curl.close()
                
                    outfile.close()
                    self.Message( "Results saved in %s" % DestFilePath )

                    # check the code, return 1 if successfull
                    if http_result == self.HTTP_SUCCESS:
                        self.Message( "Successfull!" )
                        return 1
                    else:
                        self.Message( "Failure, resultant http code: %d" % \
                                      http_result )

                except pycurl.error, err:
                    errno, errstr= err
                    self.Error( "connect to %s failed; curl error %d: '%s'\n" %
                       (server,errno,errstr) )
        
                if not outfile.closed:
                    try:
                        os.unlink(DestFilePath)
                        outfile.close()
                    except OSError:
                        pass

            else:
                self.Message( "Fetching..." )
                rc = os.system(cmdline)
                self.Message( "Done." )
                
                if rc != 0:
                    try:
                        os.unlink( DestFilePath )
                    except OSError:
                        pass
                    self.Message( "Failure, resultant curl code: %d" % rc )
                    self.Message( "Removed %s" % DestFilePath )
                else:
                    self.Message( "Successfull!" )
                    return 1
            
        self.Error( "Unable to successfully contact any boot servers.\n" )
        return 0




def usage():
    print(
    """
Usage: BootServerRequest.py [options] <partialpath>
Options:
 -c/--checkcert        Check SSL certs. Ignored if -s/--ssl missing.
 -h/--help             This help text
 -o/--output <file>    Write result to file
 -s/--ssl              Make the request over HTTPS
 -v                    Makes the operation more talkative
""");  



if __name__ == "__main__":
    import getopt
    
    # check out our command line options
    try:
        opt_list, arg_list = getopt.getopt(sys.argv[1:],
                                           "o:vhsc",
                                           [ "output=", "verbose", \
                                             "help","ssl","checkcert"])

        ssl= 0
        checkcert= 0
        output_file= None
        verbose= 0
        
        for opt, arg in opt_list:
            if opt in ("-h","--help"):
                usage(0)
                sys.exit()
            
            if opt in ("-c","--checkcert"):
                checkcert= 1
            
            if opt in ("-s","--ssl"):
                ssl= 1

            if opt in ("-o","--output"):
                output_file= arg

            if opt == "-v":
                verbose= 1
    
        if len(arg_list) != 1:
            raise Exception

        partialpath= arg_list[0]
        if string.lower(partialpath[:4]) == "http":
            raise Exception

    except:
        usage()
        sys.exit(2)

    # got the command line args straightened out
    requestor= BootServerRequest(verbose)
        
    if output_file:
        requestor.DownloadFile( partialpath, None, None, ssl,
                                checkcert, output_file)
    else:
        result= requestor.MakeRequest( partialpath, None, None, ssl, checkcert)
        if result:
            print result
        else:
            sys.exit(1)
