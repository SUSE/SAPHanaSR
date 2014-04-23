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
License:        GPL-2.0
Group:          Productivity/Clustering/HA
AutoReqProv:    on
Summary:        Resource agents to control the HANA database in system replication setup
Version:        0.135
Release:        <RELEASE1>
Url:        http://scn.sap.com/community/hana-in-memory/blog/2014/04/04/fail-safe-operation-of-sap-hana-suse-extends-its-high-availability-solution
#Release:      1
Source0:        SAPHana
Source1:        SAPHanaTopology
Source2:        README
Source3:        LICENSE
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildArch:      noarch
Requires:       pacemaker > 1.1.1
Requires:       resource-agents

%description
The resource agents SAPHana and SAPHanaTopology are responsible for controlling a SAP HANA Database which is
running in system replication (SR) configuration.

For SAP HANA Databases in System Replication only the described or referenced scanios in the README file of this
package are supported. For any scenario not matching the scenarios named or referenced in the README file
please contact SUSE at SAP LinuxLab (sap-lab@suse.de).

The following SCN blog gives a first overwiew about running SAP HANA in system replication with our resource agents:
http://scn.sap.com/community/hana-in-memory/blog/2014/04/04/fail-safe-operation-of-sap-hana-suse-extends-its-high-availability-solution



Authors:
--------
    Fabian Herschel

%prep
%setup -n %{name} -c -T

%build
cp %{S:0} .
cp %{S:1} .
cp %{S:2} .
cp %{S:3} .

%clean
test "$RPM_BUILD_ROOT" != "/" && rm -rf $RPM_BUILD_ROOT

%install
mkdir -p %{buildroot}/usr/lib/ocf/resource.d/suse
mkdir -p %{buildroot}%{_docdir}/%{name}
install -m 0755 SAPHana         %{buildroot}/usr/lib/ocf/resource.d/suse
install -m 0755 SAPHanaTopology %{buildroot}/usr/lib/ocf/resource.d/suse
install -m 0444 LICENSE         %{buildroot}/%{_docdir}/%{name}
install -m 0444 README          %{buildroot}/%{_docdir}/%{name}

%files
%defattr(-,root,root)
%dir /usr/lib/ocf
%dir /usr/lib/ocf/resource.d
%dir /usr/lib/ocf/resource.d/suse
/usr/lib/ocf/resource.d/suse/SAPHana
/usr/lib/ocf/resource.d/suse/SAPHanaTopology
%dir %{_docdir}/%{name}
%doc %{_docdir}/%{name}/README
%doc %{_docdir}/%{name}/LICENSE

%changelog
