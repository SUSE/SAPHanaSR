#
# spec file for package SAPHanaSR
#
# Copyright (c) 2013-2014 SUSE Linux Products GmbH, Nuernberg, Germany.
# Copyright (c) 2014-2016 SUSE Linux GmbH, Nuernberg, Germany.
# Copyright (c) 2017-2022 SUSE LLC.
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
Version:        1.001.1
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
The resource agents SAPHanaController and SAPHanaTopology are responsible for controlling
a SAP HANA Database which is running in system replication (SR) configuration.

For SAP HANA Databases in System Replication only the described or referenced scenarios 
described at https://documentation.suse.com/sbp/sap/ are supported. For any scenario not matching the scenarios
named or referenced in our setup guides please contact SUSE services.

The following SUSE blog series gives a good overview about running SAP HANA in System Replication
in the SUSE cluster:
https://www.suse.com/c/tag/towardszerodowntime/

Authors:
--------
    Angela Briel
    Fabian Herschel
    Lars Pinne

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

# resource agents (ra) and ra-libraries
mkdir -p %{buildroot}/usr/lib/%{name}
install -m 0755 ra/SAPHana* %{buildroot}/usr/lib/ocf/resource.d/suse/
install -m 0644 ra/saphana-*-lib %{buildroot}/usr/lib/%{name}

# HA/DR hook provider
install -m 0644 srHook/SAPHanaSR.py %{buildroot}/usr/share/%{name}/
install -m 0644 srHook/susTkOver.py %{buildroot}/usr/share/%{name}/
install -m 0644 srHook/susCostOpt.py %{buildroot}/usr/share/%{name}/
install -m 0644 srHook/susChkSrv.py %{buildroot}/usr/share/%{name}/
install -m 0444 srHook/global.ini %{buildroot}/usr/share/%{name}/samples
install -m 0444 srHook/global.ini_TakeoverBlocker %{buildroot}/usr/share/%{name}/samples
install -m 0444 srHook/global.ini_CostOptMemConfig %{buildroot}/usr/share/%{name}/samples

# icons for SAPHanaSR-monitor
install -m 0444 icons/* %{buildroot}/usr/share/%{name}/icons

# manual pages
install -m 0444 man/*.7.gz %{buildroot}%{_mandir}/man7
install -m 0444 man/*.8.gz %{buildroot}%{_mandir}/man8

# auxiliary Perl library and test scripts
#install -m 0555 test/SAPHanaSR-testDriver %{buildroot}/usr/share/%{name}/tests
install -m 0555 test/SAPHanaSR-monitor %{buildroot}/usr/sbin
install -m 0555 test/SAPHanaSR-showAttr %{buildroot}/usr/sbin
install -m 0555 test/SAPHanaSR-replay-archive %{buildroot}/usr/sbin
install -m 0555 test/SAPHanaSR-filter %{buildroot}/usr/sbin
install -m 0555 test/SAPHanaSR-hookHelper %{buildroot}/usr/sbin
install -m 0555 test/SAPHanaSR-manageProvider %{buildroot}/usr/sbin
install -m 0444 test/SAPHanaSRTools.pm %{buildroot}/usr/lib/%{name}

# README and LICENSE
install -m 0444 doc/LICENSE %{buildroot}%{_docdir}/%{name}
install -m 0444 doc/README  %{buildroot}%{_docdir}/%{name}

## TODO PRIO1: NG - check the wizard files
#install -D -m 0644 wizard/hawk2/saphanasr.yaml %{buildroot}%{crmscr_path}/saphanasr/main.yml
#install -D -m 0644 wizard/hawk2/saphanasr_su_po.yaml %{buildroot}%{crmscr_path}/saphanasr-su-po/main.yml
#install -D -m 0644 wizard/hawk2/saphanasr_su_co.yaml %{buildroot}%{crmscr_path}/saphanasr-su-co/main.yml

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
/usr/sbin/SAPHanaSR-monitor
/usr/sbin/SAPHanaSR-showAttr
/usr/sbin/SAPHanaSR-replay-archive
/usr/sbin/SAPHanaSR-filter
/usr/sbin/SAPHanaSR-hookHelper
/usr/sbin/SAPHanaSR-manageProvider

## HAWK2 wizard for SLES 12 SP1+
#%if 0%{?sle_version} >= 120100
#%dir %{crmscr_path}/saphanasr/
#%dir %{crmscr_path}/saphanasr-su-po/
#%dir %{crmscr_path}/saphanasr-su-co/
#%{crmscr_path}/saphanasr/main.yml
#%{crmscr_path}/saphanasr-su-po/main.yml
#%{crmscr_path}/saphanasr-su-co/main.yml
#%else
#%dir /srv/www/hawk
#%dir /srv/www/hawk/config
#%dir /srv/www/hawk/config/wizard
#%dir /srv/www/hawk/config/wizard/templates
#%dir /srv/www/hawk/config/wizard/workflows
#/srv/www/hawk/config/wizard/templates/SAPHanaSR.xml
#/srv/www/hawk/config/wizard/workflows/90-SAPHanaSR.xml
#%endif
%dir %{_docdir}/%{name}
%doc %{_docdir}/%{name}/README
%doc %{_docdir}/%{name}/LICENSE
%doc %{_mandir}/man7/*
%doc %{_mandir}/man8/*

%changelog