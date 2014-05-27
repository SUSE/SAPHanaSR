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
Version:        0.146
Release:        <RELEASE1>
Url:        http://scn.sap.com/community/hana-in-memory/blog/2014/04/04/fail-safe-operation-of-sap-hana-suse-extends-its-high-availability-solution
#Release:      1
Source0:        SAPHana
Source1:        SAPHanaTopology
Source2:        README
Source3:        LICENSE
Source4:        show_SAPHanaSR_attributes
Source5:        Setup-Guide.pdf
Source6:        SAPHanaSR.xml
Source7:        90-SAPHanaSR.xml
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildArch:      noarch
Requires:       pacemaker > 1.1.1
Requires:       resource-agents

%package doc
Summary:        Setup-Guide for SAPHanaSR
Group:          Productivity/Clustering/HA

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

%description doc
This sub package includes the Setup-Guide for getting SAP HANA system replication under cluster control.

%prep
%setup -n %{name} -c -T

%build
cp %{S:0} .
cp %{S:1} .
cp %{S:2} .
cp %{S:3} .
cp %{S:4} .
cp %{S:5} .
cp %{S:6} .
cp %{S:7} .

%clean
test "$RPM_BUILD_ROOT" != "/" && rm -rf $RPM_BUILD_ROOT

%install
mkdir -p %{buildroot}/usr/lib/ocf/resource.d/suse
mkdir -p %{buildroot}%{_docdir}/%{name}
mkdir -p %{buildroot}/usr/share/%{name}/tests
mkdir -p %{buildroot}/srv/www/hawk/config/wizard/templates
mkdir -p %{buildroot}/srv/www/hawk/config/wizard/workflows
install -m 0755 SAPHana         %{buildroot}/usr/lib/ocf/resource.d/suse
install -m 0755 SAPHanaTopology %{buildroot}/usr/lib/ocf/resource.d/suse
install -m 0444 LICENSE         %{buildroot}/%{_docdir}/%{name}
install -m 0444 README          %{buildroot}/%{_docdir}/%{name}
install -m 0444 Setup-Guide.pdf %{buildroot}/%{_docdir}/%{name}
install -m 0555 show_SAPHanaSR_attributes %{buildroot}/usr/share/%{name}/tests
install -m 0444 SAPHanaSR.xml   %{buildroot}/srv/www/hawk/config/wizard/templates
install -m 0444 90-SAPHanaSR.xml  %{buildroot}/srv/www/hawk/config/wizard/workflows

%files
%defattr(-,root,root)
%dir /usr/lib/ocf
%dir /usr/lib/ocf/resource.d
%dir /usr/lib/ocf/resource.d/suse
/usr/lib/ocf/resource.d/suse/SAPHana
/usr/lib/ocf/resource.d/suse/SAPHanaTopology
/usr/share/%{name}
%dir /srv/www/hawk
%dir /srv/www/hawk/config
%dir /srv/www/hawk/config/wizard
%dir /srv/www/hawk/config/wizard/templates
%dir /srv/www/hawk/config/wizard/workflows
/srv/www/hawk/config/wizard/templates/SAPHanaSR.xml
/srv/www/hawk/config/wizard/workflows/90-SAPHanaSR.xml
%dir %{_docdir}/%{name}
%doc %{_docdir}/%{name}/README
%doc %{_docdir}/%{name}/LICENSE

%files doc
%defattr(-,root,root)
%doc %{_docdir}/%{name}/Setup-Guide.pdf

%changelog
