#!/usr/bin/python
#
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
    Change this nodes boot state at PLC.

    The only valid transition is from reinstall to boot.  All other changes to
    the boot state of a node should be performed by the Admin, Tech or PI
    through the API or Web interface.

    The current value of the BOOT_STATE key in vars is used.
    Optionally, notify the contacts of the boot state change.
    If this is the case, the following keys/values
    should be set in vars before calling this step:
    STATE_CHANGE_NOTIFY= 1
    STATE_CHANGE_NOTIFY_MESSAGE= "<notify message>"
    The second value is a message to send the users from notify_messages.py

    Return 1 if succesfull, a BootManagerException otherwise.
    """

    log.write( "\n\nStep: Updating node boot state at PLC.\n" )

    update_vals= {}
    update_vals['boot_state']= vars['BOOT_STATE']
    try:
        BootAPI.call_api_function( vars, "BootUpdateNode", (update_vals,) )
        log.write( "Successfully updated boot state for this node at PLC\n" )
    except BootManagerException, e:
        log.write( "Unable to update boot state for this node at PLC: %s.\n" % e )

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
