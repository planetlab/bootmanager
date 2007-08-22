%define name bootmanager
%define version 3.1.15
%define release 3%{?pldistro:.%{pldistro}}%{?date:.%{date}}

Vendor: PlanetLab
Packager: PlanetLab Central <support@planet-lab.org>
Distribution: PlanetLab 4.1
URL: http://cvs.planet-lab.org/cvs/bootmanager

Summary: The PlanetLab Boot Manager
Name: bootmanager
Version: %{version}
Release: %{release}
License: BSD
Group: System Environment/Base
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

Requires: tar, gnupg, sharutils, bzip2

AutoReqProv: no
%define debug_package %{nil}

%description
The PlanetLab Boot Manager securely authenticates and boots PlanetLab
nodes.

%prep
%setup -q

%build
pushd bootmanager

./build.sh
pushd support-files
./buildnode.sh -r $([ -f "/etc/fedora-release" ] && awk ' { print $4 } ' /etc/fedora-release || echo "4")
popd

popd

%install
rm -rf $RPM_BUILD_ROOT

pushd bootmanager

# Install source so that it can be rebuilt
find build.sh source | cpio -p -d -u $RPM_BUILD_ROOT/%{_datadir}/%{name}/

install -D -m 755 bootmanager.sh $RPM_BUILD_ROOT/var/www/html/boot/bootmanager.sh
for file in \
    uudecode.gz \
    PlanetLab-Bootstrap.tar.bz2 ; do
  install -D -m 644 support-files/$file $RPM_BUILD_ROOT/var/www/html/boot/$file
done

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

