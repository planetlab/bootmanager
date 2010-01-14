<?php
//
// Returns node ID of requestor
//
// Mark Huang <mlhuang@cs.princeton.edu>
// Copyright (C) 2006 The Trustees of Princeton University
//
// $Id: getnodeid.php 9469 2008-05-26 14:13:19Z thierry $ $
//

// Get admin API handle
require_once 'plc_api.php';
global $adm;

if (!empty($_REQUEST['mac_addr'])) {
  $mac_lower = strtolower(trim($_REQUEST['mac_addr']));
  $mac_upper = strtoupper(trim($_REQUEST['mac_addr']));
  $interfaces = $adm->GetInterfaces(array('mac' => array($mac_lower, $mac_upper)));
} else {
  $interfaces = $adm->GetInterfaces(array('ip' => $_SERVER['REMOTE_ADDR']));
}

if (!empty($interfaces)) {
  print $interfaces[0]['node_id'];
} else {
  print "-1";
}

?>
