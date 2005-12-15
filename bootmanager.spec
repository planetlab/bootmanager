%define name bootmanager
%define version 3.1.10
%define release 1%{?pldistro:.%{pldistro}}%{?date:.%{date}}

Vendor: PlanetLab
Packager: PlanetLab Central <support@planet-lab.org>
Distribution: PlanetLab 3.0
URL: http://cvs.planet-lab.org/cvs/bootmanager

Summary: The PlanetLab Boot Manager
Name: bootmanager
Version: %{version}
Release: %{release}
License: BSD
Group: System Environment/Base
Source0: %{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

AutoReqProv: no
%define debug_package %{nil}

%description
The PlanetLab Boot Manager securely authenticates and boots PlanetLab
nodes.

%prep
%setup -q

%build
./build.sh
make -C support-files

%install
rm -rf $RPM_BUILD_ROOT
install -D -m 755 bootmanager.sh $RPM_BUILD_ROOT/var/www/html/boot/bootmanager.sh
for tarball in \
    alpina-BootLVM.tar.gz \
    alpina-PartDisks.tar.gz \
    PlanetLab-Bootstrap.tar.bz2 ; do
  install -D -m 644 support-files/$tarball $RPM_BUILD_ROOT/var/www/html/boot/$tarball
done

# If run under sudo, allow user to delete the build directory
if [ -n "$SUDO_USER" ] ; then
    chown -R $SUDO_USER .
fi

%clean
rm -rf $RPM_BUILD_ROOT

# If run under sudo, allow user to delete the built RPM
if [ -n "$SUDO_USER" ] ; then
    chown $SUDO_USER %{_rpmdir}/%{_arch}/%{name}-%{version}-%{release}.%{_arch}.rpm
fi

%post
cat <<EOF
Remember to GPG sign /var/www/html/boot/bootmanager.sh with the
PlanetLab private key.
EOF

%files
%defattr(-,root,root,-)
/var/www/html/boot/*

%changelog
* Fri Sep  2 2005 Mark Huang <mlhuang@cotton.CS.Princeton.EDU> - 
- Initial build.

