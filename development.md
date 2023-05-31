
## Branch handling

- `maintenance-classic` contains all bugfixes and features needed and delivered for the current released SAPHanaSR (Scale-Up)
  This branch is based on `master` branch (renamed at 27.04.2023), the tag `classic-start` will mark the starting point for this branch.
  All future bugfixing and feature enhancements for the released SAPHanaSR will take place in this branch (via PRs)
  All changes to this branch need to be backward compatible to not distract the installed customer base.

- `main` formerly `angi` contains all bugfixing and features for the future **SAP HANA System Replication - A New Generation Interface**

- `stable` contains a snapshot of `main`, which represents the current build release package SAPHanaSR-angi. A corresponding tag (e.g. a1.001.4-TP) will mark the release. The branch is currently set to 'read-only'

- `devel2023` may contain the current ongoing development of a feature. All bugfixes added to `main` need to be merged to this develoment branch too. After finishing the development and first tests this branch will be merged to `main` to be ready for release in `stable`.

- `*bscxxxxxx*` contains the development for a complex bugfixing. The branch name should reflect the bugzilla bugnumber. After merge to `main` or `maintenance-classic` the branch will be deleted.


## File structure in main

- `icons` contains the icons needed for SAPHanaSR-monitor;
- `man` contains manual pages;
- `ra` contains the actual resource agents, `SAPHanaController` and `SAPHanaTopology`. Additional it contains the new libraries (for now);
- `srHook` contains the HA/DR provider;
- `test` contains a semi automatic tester for SAPHanaSR-angi;
- `tools` contains the Perl auxiliary library and scripts that are installed to `/usr/sbin`;
- `wizard` contains the wizards for HAWK2 and CRM scripts (SLES 12 SP1 and above).


## Testing

To-be-continued :smile:
