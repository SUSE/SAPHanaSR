# <div align="center"> SAPHanaSR-angi - SAP HANA System Replication <br> A New Generation Interface </div>

The SUSE resource agents to control the SAP HANA database in system replication setups

[![Build Status](https://github.com/SUSE/SAPHanaSR/actions/workflows/ChecksAndLinters.yml/badge.svg?branch=angi)](https://github.com/SUSE/SAPHanaSR/actions/workflows/ChecksAndLinters.yml/badge.svg?branch=angi)


## Introduction

SAPHanaSR-angi provides an automatic failover between SAP HANA nodes with configured System Replication in HANA. Currently Scale-Up setups are targeted.

CIB attributes are not backward compatible between SAPHanaSR-angi and SAPHanaSR. So there is currently no easy migration path.

This technology is included in the SUSE Linux Enterprise Server for SAP Applications 15 (as technology preview), via the RPM package with the same name.

System replication will help to replicate the database data from one node to another node in order to compensate for database failures. With this mode of operation, internal SAP HANA high-availability (HA) mechanisms and the Linux cluster have to work together.

The SAPHanaController resource agent performs the actual check of the SAP HANA database instances and is configured as a promotable multi-state resource.
Managing the two SAP HANA instances means that the resource agent controls the start/stop of the instances. In addition the resource agent is able to monitor the SAP HANA databases on landscape host configuration level.

For this monitoring the resource agent relies on interfaces provided by SAP.

As long as the HANA landscape status is not "ERROR" the Linux cluster will not act. The main purpose of the Linux cluster is to handle the takeover to the other site.

Only if the HANA landscape status indicates that HANA can not recover from the failure and the replication is in sync, then Linux will act.

An important task of the resource agent is to check the synchronisation status of the two SAP HANA databases. If the synchronisation is not "SOK", then the
cluster avoids to take over to the secondary side, if the primary fails. This is to improve the data consistency.

For more information, refer to the ["Supported High Availability Solutions by SLES for SAP Applications](https://documentation.suse.com/sles-sap/sap-ha-support/html/sap-ha-support/article-sap-ha-support.html) and all the manual pages shipped with the package.


## File structure of installed package

- `/usr/share/SAPHanaSR-angi/doc` contains readme and license;
- `/usr/share/man` and it's subdirectories contains manual pages;
- `/usr/lib/ocf/resource.d/suse` contains the actual resource agents, `SAPHanaController` and `SAPHanaTopology`;
- `/usr/lib/SAPHanaSR-angi` contains the libraries for the resource agents;
- `/usr/share/SAPHanaSR-angi` contains SAP HA/DR provider hook scripts;
- `/usr/share/SAPHanaSR-angi/samples` contains examples for global ini configuration and various additional stuff;
- `/usr/bin` contains tools;


## License

See the [LICENSE](LICENSE) file for license rights and limitations.


## Contributing

If you are interested in contributing to this project, read the [CONTRIBUTING.md](CONTRIBUTING.md) for more information.


## Feedback
Do you have suggestions for improvement? Let us know!

Go to Issues, create a [new issue](https://github.com/SUSE/SAPHanaSR/issues) and describe what you think could be improved.

Feedback is always welcome!


## Development and Branches
Please read [development.md](development.md) for more information.


