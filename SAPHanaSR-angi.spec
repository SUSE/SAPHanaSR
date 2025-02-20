#
# spec file for package SAPHanaSR-angi
#
# Copyright (c) 2013-2014 SUSE Linux Products GmbH, Nuernberg, Germany.
# Copyright (c) 2014-2016 SUSE Linux GmbH, Nuernberg, Germany.
# Copyright (c) 2017-2025 SUSE LLC.
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
Version:        1.2.10
Release:        0
Url:            https://www.suse.com/c/fail-safe-operation-of-sap-hana-suse-extends-its-high-availability-solution/

Conflicts:      SAPHanaSR SAPHanaSR-ScaleOut SAPHanaSR-doc SAPHanaSR-ScaleOut-doc
BuildArch:      noarch

Source0:        %{name}-%{version}.tgz

BuildRoot:      %{_tmppath}/%{name}-%{version}-build

Requires:       pacemaker > 2.1.2
Requires:       resource-agents
Requires:       perl

# Require crmsh-scripts for the HAWK2 wizards
Requires:       crmsh >= 4.4.0
Requires:       crmsh-scripts >= 4.4.0
Requires:       python3
Requires:       /usr/bin/xmllint
%if 0%{?suse_version} >= 1600
Requires:       /usr/bin/sudo
Requires:       /usr/bin/logger
%endif
BuildRequires:  resource-agents >= 4.1.0
BuildRequires:  crmsh
BuildRequires:  crmsh-scripts

%description
SAPHanaSR-angi is "SAP HANA SR - An Next Generation Interface" for SUSE high availabilty clusters to manage SAP HANA databases with system replication.

The current version of SAPHanaSR-angi is targeting SAP HANA SR scale-up and scale-out setups.

CIB attributes are not backward compatible between SAPHanaSR-angi and SAPHanaSR. Nevertheless, SAPHanaSR and SAPHanaSR-ScaleOut can be upgraded to SAPHanaSR-angi by following the documented procedure.

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

%build
gzip man/*

%install
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}%{_docdir}/%{name}
mkdir -p %{buildroot}/usr/share/%{name}/icons
mkdir -p %{buildroot}/usr/share/%{name}/samples
mkdir -p %{buildroot}/usr/share/%{name}/samples/crm_cfg/angi-ScaleUp
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

# alert manager
install -m 0755 alert/SAPHanaSR-alert-fencing %{buildroot}/usr/bin

# crm config templates
install -m 0644 crm_cfg/angi-ScaleUp/[0-9]*_* %{buildroot}/usr/share/%{name}/samples/crm_cfg/angi-ScaleUp

# icons for SAPHanaSR-monitor
install -m 0444 icons/* %{buildroot}/usr/share/%{name}/icons

# manual pages
install -m 0444 man/*.7.gz %{buildroot}%{_mandir}/man7
install -m 0444 man/*.8.gz %{buildroot}%{_mandir}/man8

# auxiliary python library and tools
install -m 0555 tools/SAPHanaSR-showAttr %{buildroot}/usr/bin
install -m 0555 tools/SAPHanaSR-replay-archive %{buildroot}/usr/bin
install -m 0555 tools/SAPHanaSR-hookHelper %{buildroot}/usr/bin
install -m 0555 tools/SAPHanaSR-manageProvider %{buildroot}/usr/bin
install -m 0555 tools/SAPHanaSR-upgrade-to-angi-demo %{buildroot}/usr/share/%{name}/samples
install -m 0444 tools/saphana_sr_tools.py %{buildroot}/usr/lib/%{name}

%files
%defattr(-,root,root)
%dir /usr/lib/ocf
%dir /usr/lib/ocf/resource.d
%dir /usr/lib/ocf/resource.d/suse
/usr/lib/ocf/resource.d/suse/*
/usr/share/%{name}
%dir /usr/lib/%{name}
/usr/lib/%{name}/saphana-*-lib
/usr/lib/%{name}/saphana_sr_*.py
/usr/bin/SAPHanaSR-showAttr
/usr/bin/SAPHanaSR-replay-archive
/usr/bin/SAPHanaSR-hookHelper
/usr/bin/SAPHanaSR-manageProvider
/usr/bin/SAPHanaSR-alert-fencing

%license LICENSE
%dir %{_docdir}/%{name}
%doc README.md
%doc %{_mandir}/man7/*
%doc %{_mandir}/man8/*

%changelog
