#
# spec file for package SAPHanaSR
#
# Copyright (c) 2013-2014 SUSE LINUX Products GmbH, Nuernberg, Germany.
# Copyright (c) 2014-2015 SUSE LINUX GmbH, Nuernberg, Germany.
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
Version:        0.152.19
Release:        0
Url:            http://scn.sap.com/community/hana-in-memory/blog/2014/04/04/fail-safe-operation-of-sap-hana-suse-extends-its-high-availability-solution
#Release:      1
Source0:        SAPHana
Source1:        SAPHanaTopology
Source2:        README
Source3:        LICENSE
Source4:        show_SAPHanaSR_attributes
Source5:        SAPHanaSR-Setup-Guide.pdf
Source6:        SAPHanaSR.xml
Source7:        90-SAPHanaSR.xml
Source8:        ocf_suse_SAPHana.7
Source9:        ocf_suse_SAPHanaTopology.7
Source10:       SAPHanaSRTools.pm
Source11:       SAPHanaSR-monitor
Source12:       SAPHanaSR-showAttr
Source13:       SAPHanaSR-testDriver
Source14:       SAPHanaSR.7
Source15:       SAPHanaSR-showAttr.8
Source16:       SAPHanaSR-monitor.8
Source17:       saphanasr.yaml
Source18:       saphanasr_su_po.yaml
Source19:       saphanasr_su_co.yaml
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildArch:      noarch
Requires:       pacemaker > 1.1.1
Requires:       resource-agents

%if 0%{?sle_version} >= 120100
Requires:       crmsh
Requires:       crmsh-scripts >= 2.2.0
BuildRequires:  resource-agents
BuildRequires:  crmsh
BuildRequires:  crmsh-scripts
%endif

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
%if 0%{?sle_version} >= 120100
%define crmscr_path /usr/share/crmsh/scripts/
%endif


%build
cp %{S:0} .
cp %{S:1} .
cp %{S:2} .
cp %{S:3} .
cp %{S:4} .
cp %{S:5} .
cp %{S:6} .
cp %{S:7} .
cp %{S:8} .
cp %{S:9} .
cp %{S:10} .
cp %{S:11} .
cp %{S:12} .
cp %{S:13} .
cp %{S:14} .
cp %{S:15} .
cp %{S:16} .
cp %{S:17} .
cp %{S:18} .
cp %{S:19} .
gzip ocf_suse_SAPHana.7
gzip ocf_suse_SAPHanaTopology.7
gzip SAPHanaSR-monitor.8
gzip SAPHanaSR-showAttr.8
gzip SAPHanaSR.7

%clean
test "$RPM_BUILD_ROOT" != "/" && rm -rf $RPM_BUILD_ROOT

%install
mkdir -p %{buildroot}/usr/sbin
mkdir -p %{buildroot}/usr/lib/ocf/resource.d/suse
mkdir -p %{buildroot}%{_docdir}/%{name}
mkdir -p %{buildroot}/usr/share/%{name}/tests
mkdir -p %{buildroot}/usr/lib/%{name}
mkdir -p %{buildroot}/usr/share/man/man7
mkdir -p %{buildroot}/usr/share/man/man8
install -m 0755 SAPHana         %{buildroot}/usr/lib/ocf/resource.d/suse
install -m 0755 SAPHanaTopology %{buildroot}/usr/lib/ocf/resource.d/suse
install -m 0444 LICENSE         %{buildroot}/%{_docdir}/%{name}
install -m 0444 README          %{buildroot}/%{_docdir}/%{name}
install -m 0444 SAPHanaSR-Setup-Guide.pdf %{buildroot}/%{_docdir}/%{name}
install -m 0555 show_SAPHanaSR_attributes %{buildroot}/usr/share/%{name}/tests
install -m 0555 SAPHanaSR-testDriver %{buildroot}/usr/share/%{name}/tests
install -m 0555 SAPHanaSR-monitor %{buildroot}/usr/sbin
install -m 0555 SAPHanaSR-showAttr %{buildroot}/usr/sbin
install -m 0444 SAPHanaSRTools.pm %{buildroot}/usr/lib/%{name}
install -m 0444 ocf_suse_SAPHana.7.gz %{buildroot}/usr/share/man/man7
install -m 0444 ocf_suse_SAPHanaTopology.7.gz %{buildroot}/usr/share/man/man7
install -m 0444 SAPHanaSR-monitor.8.gz %{buildroot}/usr/share/man/man8
install -m 0444 SAPHanaSR-showAttr.8.gz %{buildroot}/usr/share/man/man8
install -m 0444 SAPHanaSR.7.gz %{buildroot}/usr/share/man/man7
# crm/hawk wizard files 
%if 0%{?sle_version} >= 120100
install -D -m 0644 saphanasr.yaml %{buildroot}%{crmscr_path}/saphanasr/main.yml
install -D -m 0644 saphanasr_su_po.yaml %{buildroot}%{crmscr_path}/saphanasr-su-po/main.yml
install -D -m 0644 saphanasr_su_co.yaml %{buildroot}%{crmscr_path}/saphanasr-su-co/main.yml
%else
mkdir -p %{buildroot}/srv/www/hawk/config/wizard/templates
mkdir -p %{buildroot}/srv/www/hawk/config/wizard/workflows
install -m 0444 SAPHanaSR.xml   %{buildroot}/srv/www/hawk/config/wizard/templates
install -m 0444 90-SAPHanaSR.xml  %{buildroot}/srv/www/hawk/config/wizard/workflows
%endif

%files
%defattr(-,root,root)
%dir /usr/lib/ocf
%dir /usr/lib/ocf/resource.d
%dir /usr/lib/ocf/resource.d/suse
/usr/lib/ocf/resource.d/suse/SAPHana
/usr/lib/ocf/resource.d/suse/SAPHanaTopology
/usr/share/%{name}
%dir %{_docdir}/%{name}
%doc %{_docdir}/%{name}/README
%doc %{_docdir}/%{name}/LICENSE
%dir /usr/lib/%{name}
/usr/lib/%{name}/SAPHanaSRTools.pm
/usr/sbin/SAPHanaSR-monitor
/usr/sbin/SAPHanaSR-showAttr
%if 0%{?sle_version} >= 120100
%dir %{crmscr_path}/saphanasr/
%dir %{crmscr_path}/saphanasr-su-po/
%dir %{crmscr_path}/saphanasr-su-co/
%{crmscr_path}/saphanasr/main.yml
%{crmscr_path}/saphanasr-su-po/main.yml
%{crmscr_path}/saphanasr-su-co/main.yml
%else
%dir /srv/www/hawk
%dir /srv/www/hawk/config
%dir /srv/www/hawk/config/wizard
%dir /srv/www/hawk/config/wizard/templates
%dir /srv/www/hawk/config/wizard/workflows
/srv/www/hawk/config/wizard/templates/SAPHanaSR.xml
/srv/www/hawk/config/wizard/workflows/90-SAPHanaSR.xml
%endif

%files doc
%defattr(-,root,root)
%doc %{_docdir}/%{name}/SAPHanaSR-Setup-Guide.pdf
%doc /usr/share/man/man7/ocf_suse_SAPHana.7.gz
%doc /usr/share/man/man7/ocf_suse_SAPHanaTopology.7.gz
%doc /usr/share/man/man7/SAPHanaSR.7.gz
%doc /usr/share/man/man8/SAPHanaSR-monitor.8.gz
%doc /usr/share/man/man8/SAPHanaSR-showAttr.8.gz

%changelog
