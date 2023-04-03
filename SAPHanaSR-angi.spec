#
# spec file for package SAPHanaSR
#
# Copyright (c) 2013-2014 SUSE Linux Products GmbH, Nuernberg, Germany.
# Copyright (c) 2014-2016 SUSE Linux GmbH, Nuernberg, Germany.
# Copyright (c) 2017-2023 SUSE LLC.
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

Name:           SAPHanaSR-angi
License:        GPL-2.0
Group:          Productivity/Clustering/HA
AutoReqProv:    on
Summary:        Resource agents to control the HANA database in system replication setup
Version:        1.001.4
Release:        0
Url:            https://www.suse.com/c/fail-safe-operation-of-sap-hana-suse-extends-its-high-availability-solution/

BuildArch:      noarch

Source0:        %{name}-%{version}.tgz

BuildRoot:      %{_tmppath}/%{name}-%{version}-build

Requires:       pacemaker > 2.1.2
Requires:       resource-agents
Requires:       perl

# Require crmsh-scripts on SLES 12 SP1+ for the new HAWK wizards
%if 0%{?sle_version} >= 120100
Requires:       crmsh >= 4.4.0
Requires:       crmsh-scripts >= 4.4.0
Requires:       python3
Requires:       /usr/bin/xmllint
BuildRequires:  resource-agents >= 4.1.0
BuildRequires:  crmsh
BuildRequires:  crmsh-scripts
%endif

%description
SAPHanaSR-angi is "SAP HANA SR - An Next Generation Interface" for SUSE high availabilty clusters to manage SAP HANA databases with system replication.

The current version of SAPHanaSR-angi is targeting SAP HANA SR scale-up setups.

CIB attributes are not backward compatible between SAPHanaSR-angi and SAPHanaSR. So there is currently no easy migration path.

SAPHanaSR-angi is shipped as technology preview.

The resource agents SAPHanaController and SAPHanaTopology are responsible for controlling a SAP HANA Database which is running in system replication (SR) configuration.

For SAP HANA Databases in System Replication only the listed scenarios at https://documentation.suse.com/sles-sap/sap-ha-support/html/sap-ha-support/article-sap-ha-support.html are supported. For any scenario not matching the scenarios named or referenced in our setup guides please contact SUSE services.

The following SUSE blog series gives a good overview about running SAP HANA in System Replication in the SUSE cluster:
https://www.suse.com/c/tag/towardszerodowntime/

Authors:
--------
    Angela Briel
    Fabian Herschel
    Lars Pinne

%prep
tar xf %{S:0}
%define crmscr_path /usr/share/crmsh/scripts/

%build
gzip man/*

%install
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}%{_docdir}/%{name}
mkdir -p %{buildroot}/usr/share/%{name}/icons
mkdir -p %{buildroot}/usr/share/%{name}/tests
mkdir -p %{buildroot}/usr/share/%{name}/samples
mkdir -p %{buildroot}/usr/lib/ocf/resource.d/suse
mkdir -p %{buildroot}/usr/lib/%{name}
mkdir -p %{buildroot}%{_mandir}/man7
mkdir -p %{buildroot}%{_mandir}/man8

# resource agents (ra) and ra-libraries
mkdir -p %{buildroot}/usr/lib/%{name}
install -m 0755 ra/SAPHana* %{buildroot}/usr/lib/ocf/resource.d/suse/
install -m 0644 ra/saphana-*-lib %{buildroot}/usr/lib/%{name}

# HA/DR hook provider
install -m 0644 srHook/susHanaSR.py %{buildroot}/usr/share/%{name}/
install -m 0644 srHook/susTkOver.py %{buildroot}/usr/share/%{name}/
install -m 0644 srHook/susCostOpt.py %{buildroot}/usr/share/%{name}/
install -m 0644 srHook/susChkSrv.py %{buildroot}/usr/share/%{name}/
install -m 0444 srHook/global.ini_* %{buildroot}/usr/share/%{name}/samples

# icons for SAPHanaSR-monitor
install -m 0444 icons/* %{buildroot}/usr/share/%{name}/icons

# manual pages
install -m 0444 man/*.7.gz %{buildroot}%{_mandir}/man7
install -m 0444 man/*.8.gz %{buildroot}%{_mandir}/man8

# auxiliary Perl library and test scripts
install -m 0555 tools/SAPHanaSR-monitor %{buildroot}/usr/bin
install -m 0555 tools/SAPHanaSR-showAttr %{buildroot}/usr/bin
install -m 0555 tools/SAPHanaSR-replay-archive %{buildroot}/usr/bin
install -m 0555 tools/SAPHanaSR-filter %{buildroot}/usr/bin
install -m 0555 tools/SAPHanaSR-hookHelper %{buildroot}/usr/bin
install -m 0555 tools/SAPHanaSR-manageProvider %{buildroot}/usr/bin
install -m 0444 tools/SAPHanaSRTools.pm %{buildroot}/usr/lib/%{name}

# README and LICENSE
#install -m 0444 LICENSE %{buildroot}%{_docdir}/%{name}
#install -m 0444 README.md  %{buildroot}%{_docdir}/%{name}/README

# wizard files for hawk2
install -D -m 0644 wizard/hawk2/saphanasr.yaml %{buildroot}%{crmscr_path}/saphanasr/main.yml
install -D -m 0644 wizard/hawk2/saphanasr_su_po.yaml %{buildroot}%{crmscr_path}/saphanasr-su-po/main.yml
install -D -m 0644 wizard/hawk2/saphanasr_su_co.yaml %{buildroot}%{crmscr_path}/saphanasr-su-co/main.yml

%files
%defattr(-,root,root)
%dir /usr/lib/ocf
%dir /usr/lib/ocf/resource.d
%dir /usr/lib/ocf/resource.d/suse
/usr/lib/ocf/resource.d/suse/*
/usr/share/%{name}
%dir /usr/lib/%{name}
/usr/lib/%{name}/SAPHanaSRTools.pm
/usr/lib/%{name}/saphana-*-lib
/usr/bin/SAPHanaSR-monitor
/usr/bin/SAPHanaSR-showAttr
/usr/bin/SAPHanaSR-replay-archive
/usr/bin/SAPHanaSR-filter
/usr/bin/SAPHanaSR-hookHelper
/usr/bin/SAPHanaSR-manageProvider

## HAWK2 wizard
%dir %{crmscr_path}/saphanasr/
%dir %{crmscr_path}/saphanasr-su-po/
%dir %{crmscr_path}/saphanasr-su-co/
%{crmscr_path}/saphanasr/main.yml
%{crmscr_path}/saphanasr-su-po/main.yml
%{crmscr_path}/saphanasr-su-co/main.yml

%license LICENSE
%dir %{_docdir}/%{name}
%doc README.md
%doc %{_mandir}/man7/*
%doc %{_mandir}/man8/*

%changelog
