# SAP HANA System Replication (Scale-Up)

## File structure

- `doc` contains readme, license and the PDF with a link to the latest best practice guides;
- `man` contains manual pages;
- `ra` contains the actual resource agents, `SAPHana` and `SAPHanaTopology`;
- `test` contains the Perl auxiliary library and scripts that are installed to `/usr/sbin` and `/usr/share/SAPHanaSR/tests`;
- `wizard` contains **two** sets of wizards, one for HAWK and another for HAWK2 and CRM scripts (SLES 12 SP1 and above).

## Building

Running `make` will create a tarball with the sources.

Additionally, it can commit the changes to the OBS, given that the `OBSPROJ` parameter is set and points to a valid local OBS package copy:
``make commit OBSPROJ=~/dev/saphanasr_obs``

Building the package locally is also possible via:
``make build OBSPROJ=~/dev/saphanasr_obs OBSTARG=SLE_12_SP2``

Some important changes!
