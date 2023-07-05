# pylint: disable=invalid-name
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

Please make sure to use our supported maintenance procedure together with this HA/DR hook as
described in the man page SAPHanaSR_maitenance_examples(7) -
EXAMPLES: * Perform an SAP HANA take-over by using SAP tools or a manual performed
takeover will be blocked.

"""

# loading classes and libraries
import os
import time

# pylint: enable=invalid-name
try:
    from hdb_ha_dr.client import HADRBase
except ImportError as e:
    print(f"Module HADRBase not found - running outside of SAP HANA? - {e}")

# parameter section
FHSRHOOKVERSION = "1.001.1"
TIME_OUT_DFLT = 30
RC_TOB = 50277

try:
    # pylint: disable-next=invalid-name
    class susTkOver(HADRBase):
        """ class for HADR hook to handle preTakeover events """

        def __init__(self, *args, **kwargs):
            # delegate construction to base class
            super().__init__(*args, **kwargs)
            method = "init"

            # read settings from global.ini
            # read sustkover_timeout
            if self.config.hasKey("sustkover_timeout"):
                self.time_out = self.config.get("sustkover_timeout")
            else:
                self.time_out = TIME_OUT_DFLT
            self.tracer.info(f"{self.__class__.__name__}.{method}()"
                             f" version {FHSRHOOKVERSION}, time_out {self.time_out}")

        def about(self):
            """ tell something about the HADR hook script """
            method = "about"
            self.tracer.info(f"{self.__class__.__name__}.{method}() version {FHSRHOOKVERSION}")
            return {"provider_company": "SUSE",
                    "provider_name": "susTkOver",  # class name
                    "provider_description": "Block manual takeover, if cluster is active",
                    "provider_version": "1.0"}

        # pylint: disable-next=unused-argument,invalid-name
        def preTakeover(self, isForce, **kwargs):
            """Pre takeover hook."""
            #
            #   * TODO PRIO1: add check, if cluster does actively manage the resource
            #   * Prerequisites:
            #   *    RA does set the same attribute as checked here (key and value)
            #   *    Sudoers does allow the query of the attribute (alternatively)
            #   *    add <sid>adm user(s) to hacluster group)
            #
            method = "preTakeover"
            start_time = time.time()
            self.tracer.info(f"{self.__class__.__name__}.{method}() called with isForce={isForce}")
            if not isForce:
                # run pre takeover code
                # run pre-check, return != 0 in case of error => will abort takeover
                my_sid = os.environ.get('SAPSYSTEMNAME')
                tout_cmd = f"timeout {self.time_out}s"
                maint_cmd = ("sudo /usr/bin/SAPHanaSR-hookHelper"
                             f" --sid={my_sid} --case=checkTakeover")
                self.tracer.info(f"{self.__class__.__name__}.{method}()"
                                 f" maint_cmd is: {maint_cmd}, tout_cmd is: {tout_cmd}")
                cmdrc = os.WEXITSTATUS(os.system(tout_cmd + " " + maint_cmd))
                if cmdrc == 0:
                    # permit cluster action sr_takeover()
                    self.tracer.info(f"{self.__class__.__name__}.{method}()"
                                     f" permit cluster action sr_takeover() cmdrc={cmdrc}")
                    sra_rc = 0
                elif cmdrc == 6:
                    # cluster connection not available, permit takeover
                    self.tracer.info(f"{self.__class__.__name__}.{method}()"
                                     "  permit non-cluster action sr_takeover()"
                                     f" because cluster connection is not available cmdrc={cmdrc}")
                    sra_rc = 0
                elif cmdrc == 99:
                    # unknown cluster command error, permit takeover
                    self.tracer.info(f"{self.__class__.__name__}.{method}()"
                                     " permit non-cluster action sr_takeover()"
                                     f" because cluster is not working properly cmdrc={cmdrc}")
                    sra_rc = 0
                elif cmdrc == 5:
                    # multi-state resource in maintenance, permit takeover
                    self.tracer.info(f"{self.__class__.__name__}.{method}()"
                                     " permit non-cluster action sr_takeover()"
                                     f" because found cluster maintenance settings (cmdrc={cmdrc})")
                    sra_rc = 0
                elif cmdrc == 7:
                    # given SID not configured in the cluster, block takeover
                    self.tracer.info(f"{self.__class__.__name__}.{method}()"
                                     " reject non-cluster action sr_takeover()"
                                     " because related SID is not configured in the cluster"
                                     f"  - missing resources (cmdrc={cmdrc})")
                elif cmdrc == 4:
                    # block takeover
                    # sr_takeover attribute not found or not set to 'T'
                    # and multi-state ressource is NOT in maintenance
                    self.tracer.info(f"{self.__class__.__name__}.{method}()"
                                     f" reject non-cluster action sr_takeover() cmdrc={cmdrc}")
                    try:
                        # take the correct rc from HANA settings
                        sra_rc = self.errorCodeClusterConfigured
                    except:  # pylint: disable=bare-except
                        # fallback for self.errorCodeClusterConfigured, if HANA does not already
                        # provide the rc codes
                        sra_rc = RC_TOB
                else:
                    # block takeover because command run-time hit timeout
                    self.tracer.info(f"{self.__class__.__name__}.{method}() timeout -"
                                     f" reject action sr_takeover() cmdrc={cmdrc},"
                                     f" timeout {self.time_out}s")
                    try:
                        # take the correct rc from HANA settings
                        sra_rc = self.errorCodeClusterConfigured
                    except:  # pylint: disable=bare-except
                        # fallback for self.errorCodeClusterConfigured, if HANA does not already
                        # provide the rc codes
                        sra_rc = RC_TOB

                self.tracer.info(f"{self.__class__.__name__}.{method}() leave preTakeover hook"
                                 f" - rc: {sra_rc},  runtime: {(time.time() - start_time)}s")
                return sra_rc

            # possible force-takeover only code
            # usually nothing to do here
            self.tracer.info(f"{self.__class__.__name__}.{method}() leave preTakeover hook"
                             f" - rc: 0, runtime: {(time.time() - start_time)}s")
            return 0

except NameError as e:
    print(f"Could not find base class ({e})")
