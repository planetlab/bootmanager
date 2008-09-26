#
# $Id$
#
%define url $URL$

%define name bootmanager
%define version 3.2
%define taglevel 13

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

%files
%defattr(-,root,root,-)
%{_datadir}/%{name}
%ghost /var/www/html/boot/bootmanager.sh
/var/www/html/boot/uudecode.gz

%changelog
* Fri Sep 26 2008 Stephen Soltesz <soltesz@cs.princeton.edu> - BootManager-3.2-13
- include latest module tweaks in current production bootmanager.

* Tue Jul 08 2008 Stephen Soltesz <soltesz@cs.princeton.edu> - BootManager-3.2-12
- correctly convert port number to int before creating HTTPSConnection() object,
- plus other changes to file to accomodate this.

* Wed Jul 02 2008 Daniel Hokka Zakrisson <daniel@hozac.com> - BootManager-3.2-11
- More hacks.

* Tue Jul 01 2008 Daniel Hokka Zakrisson <daniel@hozac.com> - BootManager-3.2-10
- Make the hack work.

* Tue Jul 01 2008 Daniel Hokka Zakrisson <daniel@hozac.com> - BootManager-3.2-9
- Ugly hack stuff.

* Fri Jun 27 2008 Faiyaz Ahmed <faiyaza@cs.princeton.edu> - BootManager-3.2-8
- move the UpdateNodeConfiguration step after the NodeUpdate step in ChainBoot

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
