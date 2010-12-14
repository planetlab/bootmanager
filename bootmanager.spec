#
# $Id$
#
%define url $URL$

%define name bootmanager
%define version 4.3
%define taglevel 19

%define release %{taglevel}%{?pldistro:.%{pldistro}}%{?date:.%{date}}

Vendor: PlanetLab
Packager: PlanetLab Central <support@planet-lab.org>
Distribution: PlanetLab %{plrelease}
URL: %(echo %{url} | cut -d ' ' -f 2)

Summary: The PlanetLab Boot Manager
Name: %{name}
Version: %{version}
Release: %{release}
License: BSD
Group: System Environment/Base
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

Requires: tar, gnupg, sharutils, bzip2, pypcilib
Requires: PLCAPI >= 4.3

# the python code packaged in these are shipped on the node as well
Requires: pypcilib pyplnet monitor-runlevelagent

AutoReqProv: no
%define debug_package %{nil}

%description
The PlanetLab Boot Manager securely authenticates and boots PlanetLab
nodes.

%prep
%setup -q

%build
gcc -shared -fPIC -ldl -Os -o source/libc-opendir-hack.so source/libc-opendir-hack.c

%install
rm -rf $RPM_BUILD_ROOT

# Install source so that it can be rebuilt
find build.sh source | cpio -p -d -u $RPM_BUILD_ROOT/%{_datadir}/%{name}/

touch bootmanager.sh
install -D -m 755 bootmanager.sh $RPM_BUILD_ROOT/var/www/html/boot/bootmanager.sh

# This is only required for 2.x bootcds.
install -D -m 644 support-files/uudecode.gz $RPM_BUILD_ROOT/var/www/html/boot/uudecode.gz

%clean
rm -rf $RPM_BUILD_ROOT

# If run under sudo
if [ -n "$SUDO_USER" ] ; then
    # Allow user to delete the build directory
    chown -h -R $SUDO_USER .
    # Some temporary cdroot files like /var/empty/sshd and
    # /usr/bin/sudo get created with non-readable permissions.
    find . -not -perm +0600 -exec chmod u+rw {} \;
    # Allow user to delete the built RPM(s)
    chown -h -R $SUDO_USER %{_rpmdir}/%{_arch}
fi

%post
cat <<EOF
Remember to GPG sign /var/www/html/boot/bootmanager.sh with the
PlanetLab private key.
EOF

# NOTE: do not run this agent when installed on a myplc.
chkconfig monitor-runlevelagent off
chkconfig --del monitor-runlevelagent

%files
%defattr(-,root,root,-)
%{_datadir}/%{name}
%ghost /var/www/html/boot/bootmanager.sh
/var/www/html/boot/uudecode.gz

%changelog
* Tue Dec 14 2010 Daniel Hokka Zakrisson <dhokka@cs.princeton.edu> - bootmanager-4.3-19
- Force removal of VG for automation.

* Fri Nov 19 2010 Daniel Hokka Zakrisson <dhokka@cs.princeton.edu> - bootmanager-4.3-18
- Use resize2fs for resizing.
- Fix typo for VSERVERS_SIZE.
- Disable time/count-based fsck.

* Fri Feb 19 2010 S.Çağlar Onur <caglar@cs.princeton.edu> - BootManager-4.3-17
- merge initrd changes from trunk

* Sat Jan 09 2010 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - BootManager-4.3-16
- support for fedora 12

* Sat Dec 19 2009 Marc Fiuczynski <mef@cs.princeton.edu> - BootManager-4.3-15
- - support for when the node is behind a NAT
- - clean up RUN_LEVEL support
- - support for early sshd

* Thu Nov 19 2009 Daniel Hokka Zakrisson <daniel@hozac.com> - BootManager-4.3-14
- Add NAT model option for nodes which don't resolve properly.

* Mon Sep 07 2009 Stephen Soltesz <soltesz@cs.princeton.edu> - BootManager-4.3-12
- Moved some configuration values from BootServerRequest.py to 'configuration' file.
- BootServerRequest takes the 'VARS' variable to read these values.
- UPLOAD_LOG_SCRIPT can point optionally to the 'upload-bmlog.php' or 'monitor/upload'
- (or any other interface that accepts a POST file)
- build.sh bundles cacerts for boot and monitor servers (if present) to
- authenticate the UPLOAD_LOG_SCRIPT.
- Previously, these certs were re-used from the bootcd, now they are bundled
- with BM.  This allows the BM to point to a completely different myplc if
- desired, and it is still secure, because the original download is
- authenticated.

* Wed Aug 26 2009 Stephen Soltesz <soltesz@cs.princeton.edu> - BootManager-4.3-11
- raise a single exception for nodes with authentication errors
- fix syntax error in MakeInitrd.py

* Mon Aug 10 2009 Stephen Soltesz <soltesz@cs.princeton.edu> - BootManager-4.3-10
- Replace UpdateBootstate with UpdateRunlevel where appropriate.
- Removed failboot and install from forced states.
- Removed checks for initrd in Validate
- Added extra messages for Validate failures, not-installed, no kernel, failed fsck
- Added libc-opendir-hack.so patch from 3.2 branch for 2.6.12 bootcds on PL.

* Mon Jun 29 2009 Marc Fiuczynski <mef@cs.princeton.edu> - BootManager-4.3-9
- Special handling for "forcedeth" ethernet NIC.

* Mon Jun 15 2009 Stephen Soltesz <soltesz@cs.princeton.edu> - BootManager-4.3-8
- include a fix for public pl dealing with old/new boot images and root
- environments

* Fri May 15 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - BootManager-4.3-7
- review selection nodefamily at bootstrapfs install-time
- now based on (1) tags (2) nodefamily and (3) defaults
- this is required on very old bootcd

* Wed Apr 29 2009 Marc Fiuczynski <mef@cs.princeton.edu> - BootManager-4.3-6
- Use modprobe module to write out /etc/modprobe.conf.

* Wed Apr 22 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - BootManager-4.3-5
- minor updates - using the new modprobe module *not* in this tag

* Wed Apr 08 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - BootManager-4.3-4
- load device mapper if needed, for centos5-based bootcd variant

* Wed Mar 25 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - BootManager-4.3-3
- renumbered 4.3
- New step StartRunLevelAgent
- various other tweaks

* Wed Jan 28 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - BootManager-4.3-2
- most of the actual network config job moved to (py)plnet
- support for RAWDISK
- network interfaces deterministically sorted
- does not use nodegroups anymore for getting node arch and other extensions
- drop yum-based extensions
- debug sshd started as early as possible
- timestamped and uploadable logs (requires upload-bmlog.php from nodeconfig/)
- cleaned up (drop support for bootcdv2)
- still needs testing

* Wed Sep 10 2008 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - BootManager-4.3-1
- reflects new names from the data model

* Sat May 24 2008 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - BootManager-3.2-7
- dont unload cpqphp

* Thu Apr 24 2008 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - BootManager-3.2-6
- changes in the state automaton logic 
- root+swap = 7G
- usb-key threshhold increased to 17 G
- bootstrafs selection logic altered - uses /etc/planetlab/nodefamily instead of GetPlcRelease

* Wed Mar 26 2008 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - BootManager-3.2-4 BootManager-3.2-5
- renamed step InstallBootstrapRPM into InstallBootstrapFS
- reviewed selection of bootstrapfs, based on nodegroups, for multi-arch deployment
- import pypcimap rather than pypciscan
- initial downlaoding of plc_config made more robust
- root and /vservers file systems mounted ext3
- calls to BootGetNodeDetails replaced with GetNodes/GetNodeNetworks
- also seems to be using session-based authentication rather than former hmac-based one

* Fri Feb 08 2008 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - bootmanager-3.2-3 bootmanager-3.2-4
- usage of wireless attributes fixed and tested
- breakpoints cleaned up (no change for production)
- less alarming message when floppy does not get unloaded

* Thu Jan 31 2008 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - bootmanager-3.2-2 bootmanager-3.2-3
- network config : support the full set of settings from ifup-wireless - see also http://svn.planet-lab.org/svn/MyPLC/tags/myplc-4.2-1/db-config
- removes legacy calls to PlanetLabConf.py 
- refrains from unloading floppy 
- first draft of the dual-method for implementing extensions (bootstrapfs-like images or yum install)

* Fri Sep  2 2005 Mark Huang <mlhuang@cotton.CS.Princeton.EDU> - 
- Initial build.

%define module_current_branch 3.2
