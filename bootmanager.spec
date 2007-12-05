#
# $Id: bootmanager.spec 856 2007-09-21 13:54:58Z thierry $
#
%define name bootmanager
%define version 3.2
%define subversion 1

%define release %{subversion}%{?pldistro:.%{pldistro}}%{?date:.%{date}}

Vendor: PlanetLab
Packager: PlanetLab Central <support@planet-lab.org>
Distribution: PlanetLab 4.2
URL: http://cvs.planet-lab.org/cvs/bootmanager

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
pushd BootManager
./build.sh
popd

%install
rm -rf $RPM_BUILD_ROOT

pushd BootManager

# Install source so that it can be rebuilt
find build.sh source | cpio -p -d -u $RPM_BUILD_ROOT/%{_datadir}/%{name}/

install -D -m 755 bootmanager.sh $RPM_BUILD_ROOT/var/www/html/boot/bootmanager.sh

# This is only required for 2.x bootcds.
install -D -m 644 support-files/uudecode.gz $RPM_BUILD_ROOT/var/www/html/boot/uudecode.gz

popd

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
/var/www/html/boot/*

%changelog
* Fri Sep  2 2005 Mark Huang <mlhuang@cotton.CS.Princeton.EDU> - 
- Initial build.
