# SAP HANA System Replication (Scale-Up)

The SUSE ScaleUp resource agents to control the SAP HANA database in system replication setups


[![Build Status](https://travis-ci.org/SUSE/SAPHanaSR.svg?branch=master)](https://travis-ci.org/SUSE/SAPHanaSR)


## Introduction

SAPHanaSR provides an automatic failover between SAP HANA nodes with configured System Replication in HANA Scale-Up setups.

This technology is included in the SUSE Linux Enterprise Server for SAP Applications 12 SP2 or later, via the RPM package with the same name.

System replication will help to replicate the database data from one node to another node in order to compensate for database failures. With this mode of operation, internal SAP HANA high-availability (HA) mechanisms and the Linux cluster have to work together.

The SAPHana resource agent performs the actual check of the SAP HANA database instances and is configured as a master/slave resource.
Managing the two SAP HANA instances means that the resource agent controls the start/stop of the instances. In addition the resource agent is able to monitor the SAP HANA databases on landscape host configuration level.

For this monitoring the resource agent relies on interfaces provided by SAP.

As long as the HANA landscape status is not "ERROR" the Linux cluster will not act. The main purpose of the Linux cluster is to handle the take-over to the other site.

Only if the HANA landscape status indicates that HANA can not recover from the failure and the replication is in sync, then Linux will act.

An important task of the resource agent is to check the synchronisation status of the two SAP HANA databases. If the synchronisation is not "SOK", then the
cluster avoids to takeover to the secondary side, if the primary fails. This is to improve the data consistency.

For more information, refer to the ["SAP HANA System Replication Scale-Up - Performance Optimized Scenario" Best Practices guide](https://documentation.suse.com/sbp/all/single-html/SLES4SAP-hana-sr-guide-PerfOpt-12/)

**Note:** To automate SAP HANA SR in scale-out setups, please refer to the [SAPHanaSR-ScaleOut repository](https://github.com/SUSE/SAPHanaSR-ScaleOut) instead.


## File structure

- `doc` contains readme, license and the PDF with a link to the latest best practice guides;
- `man` contains manual pages;
- `ra` contains the actual resource agents, `SAPHana` and `SAPHanaTopology`;
- `test` contains the Perl auxiliary library and scripts that are installed to `/usr/sbin` and `/usr/share/SAPHanaSR/tests`;
- `wizard` contains **two** sets of wizards, one for HAWK and another for HAWK2 and CRM scripts (SLES 12 SP1 and above).


## License

See the [LICENSE](LICENSE) file for license rights and limitations.


## Contributing

If you are interested in contributing to this project, read the [CONTRIBUTING.md](CONTRIBUTING.md) for more information.


## Feedback
Do you have suggestions for improvement? Let us know!

Go to Issues, create a [new issue](https://github.com/SUSE/SAPHanaSR/issues) and describe what you think could be improved.

Feedback is always welcome!



