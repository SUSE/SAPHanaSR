#
# spec file for package SAPHanaSR
#
# Copyright (c) 2013-2014 SUSE Linux Products GmbH, Nuernberg, Germany.
# Copyright (c) 2014-2016 SUSE Linux GmbH, Nuernberg, Germany.
# Copyright (c) 2017-2019 SUSE LLC.
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.
#
# Please submit bugfixes or comments via http://bugs.opensuse.org/

Name:           SAPHanaSR
License:        GPL-2.0
Group:          Productivity/Clustering/HA
AutoReqProv:    on
Summary:        Resource agents to control the HANA database in system replication setup
Version:        0.153.2
Release:        0
Url:            http://scn.sap.com/community/hana-in-memory/blog/2014/04/04/fail-safe-operation-of-sap-hana-suse-extends-its-high-availability-solution

BuildArch:      noarch

Source0:        %{name}-%{version}.tgz

BuildRoot:      %{_tmppath}/%{name}-%{version}-build

Requires:       pacemaker > 1.1.1
Requires:       resource-agents

# Require crmsh-scripts on SLES 12 SP1+ for the new HAWK wizards
%if 0%{?sle_version} >= 120100
Requires:       crmsh
Requires:       crmsh-scripts >= 2.2.0
BuildRequires:  resource-agents
BuildRequires:  crmsh
BuildRequires:  crmsh-scripts
%endif

%package doc
Summary:        Setup Guide for SAPHanaSR
Group:          Productivity/Clustering/HA

%description
The resource agents SAPHana and SAPHanaTopology are responsible for controlling
a SAP HANA Database which is running in system replication (SR) configuration.

For SAP HANA Databases in System Replication only the described or referenced scenarios in
the README file of this package are supported. For any scenario not matching the scenarios
named or referenced in the README file please contact SUSE at SAP LinuxLab (sap-lab@suse.de).

The following SCN blog gives a first overwiew about running SAP HANA in System Replication with
our resource agents:
http://scn.sap.com/community/hana-in-memory/blog/2014/04/04/fail-safe-operation-of-sap-hana-suse-extends-its-high-availability-solution

Authors:
--------
    Fabian Herschel


%description doc
This subpackage includes the Setup Guide and manual pages for getting
SAP HANA system replication under cluster control.


%prep
tar xf %{S:0}

%if 0%{?sle_version} >= 120100
    %define crmscr_path /usr/share/crmsh/scripts/
%endif


%build
gzip man/*


%install
mkdir -p %{buildroot}/usr/sbin
mkdir -p %{buildroot}%{_docdir}/%{name}
mkdir -p %{buildroot}/usr/share/%{name}/icons
mkdir -p %{buildroot}/usr/share/%{name}/tests
mkdir -p %{buildroot}/usr/share/%{name}/samples
mkdir -p %{buildroot}/usr/lib/ocf/resource.d/suse
mkdir -p %{buildroot}/usr/lib/%{name}
mkdir -p %{buildroot}%{_mandir}/man7
mkdir -p %{buildroot}%{_mandir}/man8

# resource agents
install -m 0755 ra/* %{buildroot}/usr/lib/ocf/resource.d/suse/

# HA/DR hook provider
install -m 0644 srHook/SAPHanaSR.py %{buildroot}/usr/share/%{name}/
install -m 0444 srHook/global.ini %{buildroot}/usr/share/%{name}/samples

# icons for SAPHanaSR-monitor
install -m 0444 icons/* %{buildroot}/usr/share/%{name}/icons

# documentation
install -m 0444 doc/* %{buildroot}/%{_docdir}/%{name}

# manual pages
install -m 0444 man/*.7.gz %{buildroot}%{_mandir}/man7
install -m 0444 man/*.8.gz %{buildroot}%{_mandir}/man8

# auxiliary Perl library and test scripts
#install -m 0555 test/SAPHanaSR-testDriver %{buildroot}/usr/share/%{name}/tests
install -m 0555 test/SAPHanaSR-monitor %{buildroot}/usr/sbin
install -m 0555 test/SAPHanaSR-showAttr %{buildroot}/usr/sbin
install -m 0555 test/SAPHanaSR-replay-archive %{buildroot}/usr/sbin
install -m 0555 test/SAPHanaSR-filter %{buildroot}/usr/sbin
install -m 0444 test/SAPHanaSRTools.pm %{buildroot}/usr/lib/%{name}

# crm/hawk wizard files
%if 0%{?sle_version} >= 120100
# SLES 12 SP1+ and HAWK2
install -D -m 0644 wizard/hawk2/saphanasr.yaml %{buildroot}%{crmscr_path}/saphanasr/main.yml
install -D -m 0644 wizard/hawk2/saphanasr_su_po.yaml %{buildroot}%{crmscr_path}/saphanasr-su-po/main.yml
install -D -m 0644 wizard/hawk2/saphanasr_su_co.yaml %{buildroot}%{crmscr_path}/saphanasr-su-co/main.yml
%else
# older versions of SLES and HAWK1
mkdir -p %{buildroot}/srv/www/hawk/config/wizard/templates
mkdir -p %{buildroot}/srv/www/hawk/config/wizard/workflows
install -m 0444 wizard/hawk1/SAPHanaSR.xml   %{buildroot}/srv/www/hawk/config/wizard/templates
install -m 0444 wizard/hawk1/90-SAPHanaSR.xml  %{buildroot}/srv/www/hawk/config/wizard/workflows
%endif


%files
%defattr(-,root,root)
%dir /usr/lib/ocf
%dir /usr/lib/ocf/resource.d
%dir /usr/lib/ocf/resource.d/suse
/usr/lib/ocf/resource.d/suse/*
/usr/share/%{name}
%dir /usr/lib/%{name}
/usr/lib/%{name}/SAPHanaSRTools.pm
%dir %{_docdir}/%{name}
%doc %{_docdir}/%{name}/README
%doc %{_docdir}/%{name}/LICENSE
/usr/sbin/SAPHanaSR-monitor
/usr/sbin/SAPHanaSR-showAttr
/usr/sbin/SAPHanaSR-replay-archive
/usr/sbin/SAPHanaSR-filter

# HAWK2 wizard for SLES 12 SP1+
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
%doc %{_mandir}/man7/ocf_suse_SAPHana.7.gz
%doc %{_mandir}/man7/ocf_suse_SAPHanaTopology.7.gz
%doc %{_mandir}/man7/SAPHanaSR_maintenance_examples.7.gz
%doc %{_mandir}/man7/SAPHanaSR.7.gz
%doc %{_mandir}/man7/SAPHanaSR.py.7.gz
%doc %{_mandir}/man8/SAPHanaSR-monitor.8.gz
%doc %{_mandir}/man8/SAPHanaSR-showAttr.8.gz
%doc %{_mandir}/man8/SAPHanaSR-replay-archive.8.gz


%changelog
