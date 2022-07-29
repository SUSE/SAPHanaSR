"""
# SAPHana
# Author:       Fabian Herschel, June 2020
# License:      GNU General Public License (GPL)
# Copyright:    (c) 2022 SUSE LLC

susTkOver needs SAP HANA 2.0 SPS4 (2.00.040.00) as minimum version

To use this HA/DR hook provide please add the following lines (or similar) to your global.ini:
    [ha_dr_provider_susTkOver]
    provider = susTkOver
    path = /usr/share/SAPHanaSR
    sustkover_timeout = 30
    execution_order = 1

    [trace]
    ha_dr_sustkover = info

Please make sure to use our supported maintenance procedure together with this HA/DR hook as described in the man page SAPHanaSR_maitenance_examples(7) - EXAMPLES: * Perform an SAP HANA take-over by using SAP tools
or a manual performed takeover will be blocked.

"""

# loading classes and libraries
import os
import time

try:
    from hdb_ha_dr.client import HADRBase
except ImportError as e:
    print("Module HADRBase not found - running outside of SAP HANA? - {0}".format(e))

# parameter section
fhSRHookVersion = "0.160.2"
TIME_OUT_DFLT = 30
RC_TOB = 50277

try:
    class susTkOver(HADRBase):

        def __init__(self, *args, **kwargs):
            # delegate construction to base class
            super(susTkOver, self).__init__(*args, **kwargs)
            method = "init"

            # read settings from global.ini
            # read sustkover_timeout
            if self.config.hasKey("sustkover_timeout"):
                self.time_out = self.config.get("sustkover_timeout")
            else:
                self.time_out = TIME_OUT_DFLT
            self.tracer.info("{0}.{1}() version {2}, time_out {3}".format(self.__class__.__name__, method, fhSRHookVersion, self.time_out))

        def about(self):
            method = "about"
            self.tracer.info("{0}.{1}() version {2}".format(self.__class__.__name__, method, fhSRHookVersion))
            return {"provider_company": "SUSE",
                    "provider_name": "susTkOver",  # class name
                    "provider_description": "Inform Cluster about SR state",
                    "provider_version": "1.0"}

        def preTakeover(self, isForce, **kwargs):
            """Pre takeover hook."""
            """
               * TODO PRIO1: add check, if cluster does actively manage the resource
               * Prerequisites:
               *    RA does set the same attribute as checked here (key and value)
               *    Sudoers does allow the query of the attribute (alternatively add <sid>adm user(s) to hacluster group)
            """
            method = "preTakeover"
            start_time = time.time()
            self.tracer.info("{0}.{1}() called with isForce={2}".format(self.__class__.__name__, method, isForce))
            if not isForce:
                # run pre takeover code
                # run pre-check, return != 0 in case of error => will abort takeover
                my_sid = os.environ.get('SAPSYSTEMNAME')
                tout_cmd = "timeout {0}s".format(self.time_out)
                maint_cmd = "sudo /usr/sbin/SAPHanaSR-hookHelper --sid={0} --case=checkTakeover".format(my_sid)

                self.tracer.info("{0}.{1}() maint_cmd is: {2}, tout_cmd is: {3}".format(self.__class__.__name__, method, maint_cmd, tout_cmd))
                cmdrc = os.WEXITSTATUS(os.system(tout_cmd + " " + maint_cmd))
                if cmdrc == 0:
                    # permit cluster action sr_takeover()
                    self.tracer.info("{0}.{1}() permit cluster action sr_takeover() cmdrc={2}".format(self.__class__.__name__, method, cmdrc))
                    sra_rc = 0
                elif cmdrc == 6:
                    # cluster connection not available, permit takeover
                    self.tracer.info("{0}.{1}() permit non-cluster action sr_takeover() because cluster connection is not available (cmdrc={2})".format(self.__class__.__name__, method, cmdrc))
                    sra_rc = 0
                elif cmdrc == 99:
                    # unknown cluster command error, permit takeover
                    self.tracer.info("{0}.{1}() permit non-cluster action sr_takeover() because cluster is not working properly (cmdrc={2})".format(self.__class__.__name__, method, cmdrc))
                    sra_rc = 0
                elif cmdrc == 5:
                    # multi-state resource in maintenance, permit takeover
                    self.tracer.info("{0}.{1}() permit non-cluster action sr_takeover() because found cluster maintenance settings (cmdrc={2})".format(self.__class__.__name__, method, cmdrc))
                    sra_rc = 0
                elif cmdrc == 7:
                    # given SID not configured in the cluster, block takeover
                    self.tracer.info("{0}.{1}() reject non-cluster action sr_takeover() because related SID is not configured in the cluster - missing resources (cmdrc={2})".format(self.__class__.__name__, method, cmdrc))
                elif cmdrc == 4:
                    # block takeover
                    # sr_takeover attribute not found or not set to 'T'
                    # and multi-state ressource is NOT in maintenance
                    self.tracer.info("{0}.{1}() reject non-cluster action sr_takeover() cmdrc={2}".format(self.__class__.__name__, method, cmdrc))
                    try:
                        sra_rc = self.errorCodeClusterConfigured  # take the correct rc from HANA settings
                    except:  # pylint: disable=bare-except
                        sra_rc = RC_TOB  # fallback for self.errorCodeClusterConfigured, if HANA does not already provide the rc codes
                else:
                    # block takeover because command run-time hit timeout
                    self.tracer.info("{0}.{1}() timeout - reject action sr_takeover() cmdrc={2}, timeout {3}s".format(self.__class__.__name__, method, cmdrc, self.time_out))
                    try:
                        sra_rc = self.errorCodeClusterConfigured  # take the correct rc from HANA settings
                    except:  # pylint: disable=bare-except
                        sra_rc = RC_TOB  # fallback for self.errorCodeClusterConfigured, if HANA does not already provide the rc codes

                self.tracer.info("{0}.{1}() leave preTakeover hook - rc is {2} - runtime was ---{3} seconds ---".format(self.__class__.__name__, method, sra_rc, (time.time() - start_time)))
                return sra_rc

            # possible force-takeover only code
            # usually nothing to do here
            self.tracer.info("{0}.{1}() leave preTakeover hook - runtime was ---{2} seconds ---".format(self.__class__.__name__, method, (time.time() - start_time)))
            return 0

except NameError as e:
    print("Could not find base class ({0})".format(e))
