# Version: 2022-07-07 11:55 



0. Content
   1. Installing the package
   2. Enabling the new HADR provider hook script
   3. Extracting hook script entries from HANA tracefiles
   4. Disabling the new HADR provider hook script
   5. Requirements and limits



1. Installing the package

# md5sum SAPHanaSR-alfa.tgz
...
# tar -zxf SAPHanaSR-alfa.tgz -C /
# find /usr/share/SAPHanaSR-alfa/

Note: The find shows what you got with the package.



2. Enabling the new HADR provider hook script

2.1 Enabling the HADR provider

In HANA global.ini the section [ha_dr_provider_suschksrv] needs to be added:
---  
[ha_dr_provider_suschksrv]
provider = susChkSrv
path = /usr/share/SAPHanaSR-alfa/
execution_order = 2
action_on_lost = kill
---
Then the HADR provider hook script needs to be reloaded.
The config change and reload have to be done at both sites.
The hook action on lost hdbindexserver process is controlled by parameter
"action_on_lost = [ ignore | stop | kill ]".
The related actions are:
- ignore	do nothing
- stop		HDB stop
- kill		HDB kill-9
That action should return faster than the hook script stop_timeout.
Default is 20 seconds, i.e. "stop_timeout = 20".

An example procedure for enabling the hook script looks like:
---
# su - <sid>adm
~> cdcoc; cp global.ini global.ini.BAK
~> vi global.ini
...
~> grep -A4 "^\[ha_dr_provider_suschksrv\]" global.ini
[ha_dr_provider_suschksrv]
provider = susChkSrv
path = /usr/share/SAPHanaSR-alfa/
execution_order = 2
action_on_lost = kill

~> date; hdbnsutil -reloadHADRProviders; echo rc: $?


2.2 Checking the HADR provider related HANA trace entries

~> cdtrace; grep "HADR.*load.*susChkSrv" nameserver_*.trc | tail -3
... 
... loading HA/DR Provider 'susChkSrv' from /usr/share/SAPHanaSR-alfa/
~> grep "ha_dr_susChkSrv.*init" nameserver_*.trc | tail -3
...
... susChkSrv.init() version 0.3.1, parameter info: stop_timeout=20 action_on_lost=kill
~> exit
---
Note: The grep shows what has been logged.



3. Extracting hook script entries from HANA tracefiles

The hook script entries can be extracted from HANA nameserver tracefiles on the
master nameserver.

An example for extracting hook script runtimes on the master nameserver:
---
# su - <sid>adm
~> cdtrace; egrep 'susChk.*(LOST:|STOP:|START:|DOWN:|TAKEOVER:|init|load|fail)' nameserver_*.trc | tail -20
...
... susChkSrv.py(00152) : START: indexserver event looks like graceful tenant start
...
... susChkSrv.py(00140) : STOP: indexserver event looks like graceful instance stop
...
... susChkSrv.py(00144) : DOWN: indexserver event looks like graceful tenant stop
...
... susChkSrv.py(00134) : TAKEOVER: indexserver event looks like a takeover event
...
... susChkSrv.py(00129) : LOST: indexserver event looks like a lost indexserver
... susChkSrv.py(00174) : LOST: kill instance. action_on_lost=kill
~> exit
---



4. Disabling the new HADR provider hook script

4.1 Disabling the HADR provider completely

The new HADR provider hook script might be disabled after the tests.

In HANA global.ini the section [ha_dr_provider_suschksrv] needs to be removed.
Then the HADR provider hook script needs to be reloaded.
The config change and reload have to be done at both sites.
Finally it might a good idea to remove the directory /usr/share/SAPHanaSR-alfa/
at both sites.


4.2 Setting the HADR provider action to ignore

As an alternative the HADR provider could be keep loaded into SAP HANA, but the
hook script should neither kill nor stop SAP HANA in an indexsever lost event.

In this case change the parameter 'action_on_lost' to value 'ignore'. With that
action the event is only mentioned in the trace file, but no action as kill or
stop is beeing started.

After changing the value in global.ini the HADR provider needs to be reloaded
as documented in section 2.1.

An example procedure for changing the hook script action to "ignore" looks like:
---
# su - <sid>adm
~> cdcoc; cp global.ini global.ini.BAK2
~> vi global.ini
...
~> grep -A4 "^\[ha_dr_provider_suschksrv\]" global.ini
[ha_dr_provider_suschksrv]
provider = susChkSrv
path = /usr/share/SAPHanaSR-alfa/
execution_order = 2
action_on_lost = ignore

~> date; hdbnsutil -reloadHADRProviders; echo rc: $?

Checking the HADR provider related HANA trace entries:

~> cdtrace; grep "HADR.*load.*susChkSrv" nameserver_*.trc | tail -3
... 
... loading HA/DR Provider 'susChkSrv' from /usr/share/SAPHanaSR-alfa/
~> grep "ha_dr_susChkSrv.*init" nameserver_*.trc | tail -3
...
... susChkSrv.init() version 0.3.1, parameter info: stop_timeout=20 action_on_lost=ignore
~> exit
---
Note: The grep shows what has been logged. The action_on_lost is logged as set
to "ignore".



5. Requirements and limits

This hook script is a preliminary alpha version for testing purpose.
It must not be used on production systems.
The hook script runs on the HANA master nameserver only. It is not designed for
HANA scale-out systems.

The hook script has the following requirements:

1. SAP HANA 2.0 SPS05 or later provides the HA/DR provider hook method
   srServiceStateChanged() with needed parameters.

2. The hook provider needs to be added to the HANA global configuration, in
   memory and on disk (in persistence).

3. The hook script action_on_lost should return faster than the stop_timeout.

If an HANA takeover attempt was blocked before, the hook script may report a later
occuring indexserver recovery as a successful takeover.

#
