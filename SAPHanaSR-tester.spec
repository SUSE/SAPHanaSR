#
# spec file for package SAPHanaSR
#
# Copyright (c) 2023 SUSE LLC.
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
Version:        1.2.1
Release:        0
Url:            https://www.suse.com/c/fail-safe-operation-of-sap-hana-suse-extends-its-high-availability-solution/

BuildArch:      noarch

Source0:        %{name}-%{version}.tgz

BuildRoot:      %{_tmppath}/%{name}-%{version}-build

Requires:       python3

%description
SAPHanaSR-tester is a suite for semi-automated tests of SAPHanaSR clusters. First focussed test-scenarios are angi-ScaleUp and angi-ScaleOut (e.g. for ERP systems).

The test cases are described in JSON files. Each test is separated into one ore multiple steps. For each step there is an expectation about the SAPHanaSR attributes, which needs to match.
Additionally each step defines the 'next' step and an optional action to be triggered if the step status has been reached (all expectations match).

The following SUSE blog series gives a good overview about running SAP HANA in System Replication in the SUSE cluster:
https://www.suse.com/c/tag/towardszerodowntime/

Authors:
--------
    Fabian Herschel

%prep
tar xf %{S:0}
#%define crmscr_path /usr/share/crmsh/scripts/

%build
#gzip man/*

%install
mkdir -p %{buildroot}/usr/bin
#mkdir -p %{buildroot}%{_docdir}/%{name}
mkdir -p %{buildroot}/usr/share/%{name}
mkdir -p %{buildroot}/usr/lib/%{name}
#mkdir -p %{buildroot}%{_mandir}/man7
#mkdir -p %{buildroot}%{_mandir}/man8

# test engine itself
mkdir -p %{buildroot}/usr/lib/%{name}
install -m 0755 test/SAPHanaSR-* %{buildroot}/usr/bin
install -m 0644 test/saphana_sr_test.py %{buildroot}/usr/lib/%{name}

# test help programs, test loops and test calls
install -m 0755 test/cs_* %{buildroot}/usr/bin
install -m 0755 test/test_* %{buildroot}/usr/bin
install -m 0755 test/callTest* %{buildroot}/usr/bin
install -m 0755 test/loopTests* %{buildroot}/usr/bin

# test definitions
pwd
ls test/json
cp -va test/json %{buildroot}/usr/share/%{name}

# manual pages
#install -m 0444 man/*.7.gz %{buildroot}%{_mandir}/man7
#install -m 0444 man/*.8.gz %{buildroot}%{_mandir}/man8

%files
%defattr(-,root,root)
/usr/share/%{name}
%dir /usr/lib/%{name}
/usr/lib/%{name}/saphana_sr_*.py
/usr/bin/*

%license LICENSE
#%dir %{_docdir}/%{name}
%doc README.md
#%doc %{_mandir}/man7/*
#%doc %{_mandir}/man8/*

%changelog
