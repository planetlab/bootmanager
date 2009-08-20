#!/usr/bin/python

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.


import xmlrpclib
import xml.parsers.expat
import hmac
import string
import sha
import cPickle
import utils

from Exceptions import *

stash = None

def create_auth_structure( vars, call_params ):
    """
    create and return an authentication structure for a Boot API
    call. Vars contains the boot manager runtime variables, and
    call_params is a tuple of the parameters that will be passed to the
    API call. Return None if unable to (typically due to missing
    keys in vars, such as node_id or node_key)
    """

    auth= {}

    try:
        auth_session = {}
        auth_session['AuthMethod'] = 'session'

        if not vars.has_key('NODE_SESSION'):
            # Try to load /etc/planetlab/session if it exists.
            sessionfile = open('/etc/planetlab/session', 'r')
            session = sessionfile.read().strip()

            auth_session['session'] = session
            # Test session.  Faults if it's no good.
            vars['API_SERVER_INST'].AuthCheck(auth_session)
            vars['NODE_SESSION'] = session

            sessionfile.close()
        else:
            auth_session['session'] = vars['NODE_SESSION']

        auth = auth_session

    except:
        auth['AuthMethod']= 'hmac'

        try:
            auth['node_id'] = vars['NODE_ID']
            auth['node_ip'] = vars['INTERFACE_SETTINGS']['ip']
        except KeyError, e:
            return None

        node_hmac= hmac.new(vars['NODE_KEY'], "[]".encode('utf-8'), sha).hexdigest()
        auth['value']= node_hmac
        try:
            auth_session = {}
            if not vars.has_key('NODE_SESSION'):
                session = vars['API_SERVER_INST'].GetSession(auth)
                auth_session['session'] = session
                vars['NODE_SESSION'] = session
                # NOTE: save session value to /etc/planetlab/session for 
                # RunlevelAgent and future BootManager runs
                sessionfile = open('/etc/planetlab/session', 'w')
                sessionfile.write( vars['NODE_SESSION'] )
                sessionfile.close()
            else:
                auth_session['session'] = vars['NODE_SESSION']

            auth_session['AuthMethod'] = 'session'
            auth = auth_session

        except Exception, e:
            # NOTE: BM has failed to authenticate utterly.
            raise BootManagerAuthenticationException, "%s" % e

    return auth


def serialize_params( call_params ):
    """
    convert a list of parameters into a format that will be used in the
    hmac generation. both the boot manager and plc must have a common
    format. full documentation is in the boot manager technical document,
    but essentially we are going to take all the values (and keys for
    dictionary objects), and put them into a list. sort them, and combine
    them into one long string encased in a set of braces.
    """

    values= []
    
    for param in call_params:
        if isinstance(param,list) or isinstance(param,tuple):
            values += serialize_params(param)
        elif isinstance(param,dict):
            values += serialize_params(param.values())
        elif isinstance(param,xmlrpclib.Boolean):
            # bool was not a real type in Python <2.3 and had to be
            # marshalled as a custom type in xmlrpclib. Make sure that
            # bools serialize consistently.
            if param:
                values.append("True")
            else:
                values.append("False")
        else:
            values.append(unicode(param))
                
    return values

    
def call_api_function( vars, function, user_params ):
    """
    call the named api function with params, and return the
    value to the caller. the authentication structure is handled
    automatically, and doesn't need to be passed in with params.

    If the call fails, a BootManagerException is raised.
    """
    global stash

    try:
        api_server= vars['API_SERVER_INST']
    except KeyError, e:
        raise BootManagerException, "No connection to the API server exists."

    if api_server is None:
        if not stash:
            load(vars)
        for i in stash:
            if i[0] == function and i[1] == user_params:
               return i[2]
        raise BootManagerException, \
              "Disconnected operation failed, insufficient stash."

    auth= create_auth_structure(vars,user_params)
    if auth is None:
        raise BootManagerException, \
              "Could not create auth structure, missing values."
    
    params= (auth,)
    params= params + user_params

    try:
        exec( "rc= api_server.%s(*params)" % function )
        if stash is None:
            stash = []
        stash += [ [ function, user_params, rc ] ]
        return rc
    except xmlrpclib.Fault, fault:
        raise BootManagerException, "API Fault: %s" % fault
    except xmlrpclib.ProtocolError, err:
        raise BootManagerException,"XML RPC protocol error: %s" % err
    except xml.parsers.expat.ExpatError, err:
        raise BootManagerException,"XML parsing error: %s" % err


class Stash(file):
    mntpnt = '/tmp/stash'
    def __init__(self, vars, mode):
        utils.makedirs(self.mntpnt)
        try:
            utils.sysexec('mount -t auto -U %s %s' % (vars['DISCONNECTED_OPERATION'], self.mntpnt))
            # make sure it's not read-only
            f = file('%s/api.cache' % self.mntpnt, 'a')
            f.close()
            file.__init__(self, '%s/api.cache' % self.mntpnt, mode)
        except:
            utils.sysexec_noerr('umount %s' % self.mntpnt)
            raise BootManagerException, "Couldn't find API-cache for disconnected operation"

    def close(self):
        file.close(self)
        utils.sysexec_noerr('umount %s' % self.mntpnt)

def load(vars):
    global stash
    s = Stash(vars, 'r')
    stash = cPickle.load(s)
    s.close()

def save(vars):
    global stash
    if vars['DISCONNECTED_OPERATION']:
        s = Stash(vars, 'w')
        cPickle.dump(stash, s)
        s.close()
