#
# spec file for package SAPHanaSR-tester
#
# Author: Fabian Herschel
# Copyright (c) 2023-2025 SUSE LLC.
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

Name:           SAPHanaSR-tester
License:        GPL-2.0
Group:          Productivity/Clustering/HA
AutoReqProv:    on
Summary:        Test suite for SAPHanaSR clusters
Version:        1.4.0
Release:        0
Url:            https://www.suse.com/c/fail-safe-operation-of-sap-hana-suse-extends-its-high-availability-solution/

BuildArch:      noarch

Source0:        %{name}-%{version}.tgz

BuildRoot:      %{_tmppath}/%{name}-%{version}-build

Requires:       python3

%package client
Group:          Productivity/Clustering/HA
Summary:        Test suite for SAPHanaSR clusters - SAPHanaSR-tester-client is to be installed on all SAPHanaSR classic nodes
Conflicts:      SAPHanaSR-angi

%description
SAPHanaSR-tester is a suite for semi-automated tests of SAPHanaSR clusters. First focussed test-scenarios are angi-ScaleUp and angi-ScaleOut (e.g. for ERP systems).

The test cases are described in JSON files. Each test is separated into one ore multiple steps. For each step there is an expectation about the SAPHanaSR attributes, which needs to match.
Additionally each step defines the 'next' step and an optional action to be triggered if the step status has been reached (all expectations match).

The following SUSE blog series gives a good overview about running SAP HANA in System Replication in the SUSE cluster:
https://www.suse.com/c/tag/towardszerodowntime/

Authors:
--------
    Fabian Herschel

%description client
SAPHanaSR-tester-client is to be installed on all SAPHanaSR classic nodes to allow SAPHanaSR-tester to check the cluster attributes with the same method.

%prep
tar xf %{S:0}
#%define crmscr_path /usr/share/crmsh/scripts/

%build
gzip man-tester/*
gzip man-tester-client/*

%install
mkdir -p %{buildroot}/usr/bin
#mkdir -p %{buildroot}%{_docdir}/%{name}
mkdir -p %{buildroot}/usr/share/%{name}
mkdir -p %{buildroot}/usr/share/%{name}/samples/crm_cfg/angi-ScaleUp
mkdir -p %{buildroot}/usr/lib/%{name}
mkdir -p %{buildroot}%{_mandir}/man5
mkdir -p %{buildroot}%{_mandir}/man7
mkdir -p %{buildroot}%{_mandir}/man8

# test engine itself
mkdir -p %{buildroot}/usr/lib/%{name}
install -m 0755 test/tester/SAPHanaSR-* %{buildroot}/usr/bin
install -m 0644 test/tester/saphana_sr_test.py %{buildroot}/usr/lib/%{name}

# test help programs, test loops and test calls
install -m 0755 test/bin/cs_* %{buildroot}/usr/bin
install -m 0755 test/bin/callTest* %{buildroot}/usr/bin
install -m 0755 test/bin/loopTests* %{buildroot}/usr/bin
install -m 0755 test/bin/sct_* %{buildroot}/usr/bin

# client files
install -m 0755 tools/SAPHanaSR-showAttr %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/lib/SAPHanaSR-angi
install -m 0755 tools/saphana_sr_tools.py %{buildroot}/usr/lib/SAPHanaSR-angi

# test definitions
pwd
ls test/json
cp -a test/json %{buildroot}/usr/share/%{name}
cp -a test/www %{buildroot}/usr/share/%{name}
install -m 0644 crm_cfg/angi-ScaleUp/[0-9]*_* %{buildroot}/usr/share/%{name}/samples/crm_cfg/angi-ScaleUp

# manual pages
install -m 0444 man-tester/*.5.gz %{buildroot}%{_mandir}/man5
install -m 0444 man-tester/*.7.gz %{buildroot}%{_mandir}/man7
install -m 0444 man-tester/*.8.gz %{buildroot}%{_mandir}/man8

# man pages for client package
install -m 0444 man-tester-client/*.7.gz %{buildroot}%{_mandir}/man7

%files
%defattr(-,root,root)
/usr/share/%{name}
%dir /usr/lib/%{name}
/usr/lib/%{name}/saphana_sr_*.py
/usr/bin/SAPHanaSR-testCluster
/usr/bin/SAPHanaSR-checkJson
/usr/bin/SAPHanaSR-testSelect
/usr/bin/sct_*
/usr/bin/callTest*
/usr/bin/loopTests*
/usr/bin/cs_ssh
/usr/bin/SAPHanaSR-testCluster-html
%license LICENSE
%doc README.md
%doc %{_mandir}/man*/*

%files client
/usr/bin/SAPHanaSR-showAttr
/usr/lib/SAPHanaSR-angi

%changelog
