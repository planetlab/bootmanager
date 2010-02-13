<?php

// $Id$
// $URL$

// Thierry Parmentelat -- INRIA
// first draft for a revival of former (3.x?) alpina-logs in 5.0

// this needs be created with proper permissions at package install time
$logdir="/var/log/bm";

// limit: applies to uploads coming from an unrecognized IP
$limit_bytes=4*1024;

$default_hostname="unknown";

function mkdir_if_needed ($dirname) {
  if (is_dir ($dirname))
    return;
  mkdir ($dirname) or die ("Cannot create dir " . $dirname);
}
  
// Get admin API handle
require_once 'plc_api.php';
global $adm;

// find the node that these longs should belong to by looking for a node_id
// with an ip the same as the http requestor ip
$ip = $_SERVER['REMOTE_ADDR'];

$hostname=$default_hostname;
// locate hostname from DB based on this IP
$interfaces=$adm->GetInterfaces(array("ip"=>$ip));
if (! empty($interfaces) ) {
  $interface=$interfaces[0];
  $node_id=$interface['node_id'];
  $nodes=$adm->GetNodes($node_id,array("hostname"));
  if (!empty($nodes)) {
    $hostname=$nodes[0]['hostname'];
  }
 }

// store the actual data in /var/log/bm/raw/2008-11-31-20-02-onelab01.inria.fr-138.96.250.141.txt

$rawdir=$logdir . "/raw";
$date=strftime("%Y-%m-%d-%H-%M");
$log_name=$date . "-" . $hostname . "-" . $ip . ".txt";
$log_path=$rawdir . "/" . $log_name;
$month=strftime("%Y-%m");
$time=strftime("%d-%H-%M");

mkdir_if_needed ($rawdir);

////////////////////////////////////////

$log=fopen($log_path,"w") or die ("Cannot open logfile "+$log_path);

$uploaded_name= $_FILES['log']['tmp_name'];
$uploaded_size=filesize($uploaded_name);

fprintf ($log, "BootManager log created on: %s-%s\n",$month,$time);
fprintf( $log, "From IP: %s\n",$ip);
fprintf( $log, "hostname: %s\n",$hostname);
fprintf ( $log, "uploaded file: %s (%d bytes)\n",$uploaded_name,$uploaded_size);
if ( ( strcmp($hostname,$default_hostname)==0) && ( $uploaded_size >= $limit_bytes) ) {
  fprintf ( $log, "contents from an unrecognized IP address was truncated to %d bytes\n",$limit_bytes);
  $truncated=TRUE;
  $uploaded_size=$limit_bytes;
 } else {
  $truncated=FALSE;
 }

fprintf( $log, "-----------------\n\n" );
$uploaded = fopen($uploaded_name,'r');
$contents = fread($uploaded, $uploaded_size);
fclose($uploaded);
fwrite($log,$contents);
if ($truncated)
  fwrite ($log, " ..<" . "truncated" . ">..\n");
fclose($log);

////////////////////////////////////////

// create symlinks for easy browsing

// /var/log/bm/per-month/2008-11/onelab1.inria.fr/31-20-02.bmlog
$linkdir=$logdir;
$linkdir=$linkdir . "/per-month";
mkdir_if_needed ($linkdir);
$linkdir=$linkdir . "/" . $month;
mkdir_if_needed ($linkdir);
$linkdir = $linkdir . "/" . $hostname;
mkdir_if_needed ($linkdir);
$link = $linkdir . "/" . $time ;
symlink ("../../../raw/".$log_name,$link);

# /var/log/bm/per-hostname/onelab1.inria.fr/2008-11-31-20-02.bmlog
$linkdir=$logdir;
$linkdir=$linkdir . "/per-hostname";
mkdir_if_needed ($linkdir);
$linkdir=$linkdir . "/" . $hostname;
mkdir_if_needed ($linkdir);
$link = $linkdir . "/" . $month . "-" . $time ;
symlink ("../../raw/".$log_name,$link);

# /var/log/bm/per-ip/138.96.250.141/2008-11-31-20-02.bmlog
$linkdir=$logdir;
$linkdir=$linkdir . "/per-ip";
mkdir_if_needed ($linkdir);
$linkdir=$linkdir . "/" . $ip;
mkdir_if_needed ($linkdir);
$link = $linkdir . "/" . $month . "-" . $time ;
symlink ("../../raw/".$log_name,$link);

?>
