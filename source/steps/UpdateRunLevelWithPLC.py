#!/usr/bin/python

# Copyright (c) 2003 Intel Corporation
# All rights reserved.
#
# Copyright (c) 2004-2006 The Trustees of Princeton University
# All rights reserved.

from Exceptions import *
import BootAPI
import notify_messages


def Run( vars, log ):
    """
    Change this nodes run level at PLC.

    Replaces the behavior of UpdateBootStateWithPLC.  Where previously, the
    boot_state of a node would be altered by the BM, now the run_level is
    updated, and the boot_state is preserved as a record of a User's
    preference.

    The current value of the RUN_LEVEL key in vars is used.
    Optionally, notify the contacts of the run level change.
    If this is the case, the following keys/values
    should be set in vars before calling this step:
    STATE_CHANGE_NOTIFY= 1
    STATE_CHANGE_NOTIFY_MESSAGE= "<notify message>"
    The second value is a message to send the users from notify_messages.py

    Return 1 if succesfull, a BootManagerException otherwise.
    """

    log.write( "\n\nStep: Updating node run level at PLC.\n" )

    update_vals= {}
    # translate boot_state values to run_level value
    if vars['RUN_LEVEL'] in ['diag', 'diagnose', 'disabled', 'disable']:
        vars['RUN_LEVEL']='safeboot'
    update_vals['run_level']=vars['RUN_LEVEL']
    try:
        BootAPI.call_api_function( vars, "ReportRunlevel", (update_vals,) )
        log.write( "Successfully updated run level for this node at PLC\n" )
    except BootManagerException, e:
        log.write( "Unable to update run level for this node at PLC: %s.\n" % e )

    notify = vars.get("STATE_CHANGE_NOTIFY",0)

    if notify:
        message= vars['STATE_CHANGE_NOTIFY_MESSAGE']
        include_pis= 0
        include_techs= 1
        include_support= 0

        sent= 0
        try:
            sent= BootAPI.call_api_function( vars, "BootNotifyOwners",
                                             (message,
                                              include_pis,
                                              include_techs,
                                              include_support) )
        except BootManagerException, e:
            log.write( "Call to BootNotifyOwners failed: %s.\n" % e )

        if sent == 0:
            log.write( "Unable to notify site contacts of state change.\n" )

    return 1
