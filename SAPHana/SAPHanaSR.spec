#
# spec file for package SAPHanaSR
#
# Copyright (c) 2011-2012 SUSE LINUX Products GmbH, Nuernberg, Germany.
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via http://bugs.opensuse.org/
#



Name:           SAPHanaSR
License:        GPL v2 only
Group:          Productivity/Clustering/HA
AutoReqProv:    on
Summary:        Set of resource agents to control the SAPHana database in system replication setup
Version:        0.132
#Release:        0.<RELEASE5>
Release:      1
Source0:        SAPHana
Source1:        SAPHanaTopology
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildArch:      noarch
Requires:       pacemaker > 1.1.1

%description
TODO: PRIO2: TBD

http://scn.sap.com/community/hana-in-memory/blog/2014/04/04/fail-safe-operation-of-sap-hana-suse-extends-its-high-availability-solution



Authors:
--------
    Fabian Herschel

%prep
%setup -n %{name} -c -T

%build
cp %{S:0} .
cp %{S:1} .


%clean
test "$RPM_BUILD_ROOT" != "/" && rm -rf $RPM_BUILD_ROOT

%install
mkdir -p %{buildroot}/usr/lib/ocf/resource.d/suse
install -m 0755 SAPHana         %{buildroot}/usr/lib/ocf/resource.d/suse
install -m 0755 SAPHanaTopology %{buildroot}/usr/lib/ocf/resource.d/suse

%post

%files
%defattr(-,root,root)
/usr/lib/ocf/resource.d/suse/SAPHana
/usr/lib/ocf/resource.d/suse/SAPHanaTopology

%changelog
