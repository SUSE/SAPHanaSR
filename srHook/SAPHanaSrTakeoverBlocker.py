"""
# SAPHana
# Author:       Fabian Herschel, June 2020
# License:      GNU General Public License (GPL)
# Copyright:    (c) 2022 SUSE LLC

SAPHanaSrTakeoverBlocker needs SAP HANA 2.0 SPS4 (2.00.040.00) as minimum version

To use this HA/DR hook provide please add the following lines (or similar) to your global.ini:
    [ha_dr_provider_SAPHanaSrTakeoverBlocker]
    provider = SAPHanaSrTakeoverBlocker
    path = /usr/share/SAPHanaSR
    tbsrhook_timeout = 30
    execution_order = 1

    [trace]
    ha_dr_saphanasrtakeoverblocker = info

Please make sure to use our supported maintenance procedure together with this HA/DR hook as described in the man page SAPHanaSR_maitenance_examples(7) - EXAMPLES: * Perform an SAP HANA take-over by using SAP tools
or a manual performed takeover will be blocked.

"""

# loading classes and libraries
import os
import tempfile
import time

try:
    from hdb_ha_dr.client import HADRBase
except ImportError as e:
    print("Module HADRBase not found - running outside of SAP HANA? - {0}".format(e))

# parameter section
fhSRHookVersion = "0.161.0"
TIME_OUT_DFLT = 30
RC_TOB = 50277

try:
    class SAPHanaSrTakeoverBlocker(HADRBase):

        def __init__(self, *args, **kwargs):
            # delegate construction to base class
            super(SAPHanaSrTakeoverBlocker, self).__init__(*args, **kwargs)
            method = "init"

            # read settings from global.ini
            # read tbsrhook_timeout
            if self.config.hasKey("tbsrhook_timeout"):
                self.time_out = self.config.get("tbsrhook_timeout")
            else:
                self.time_out = TIME_OUT_DFLT
            self.tracer.info("{0}.{1}() version {2}, time_out {3}".format(self.__class__.__name__, method, fhSRHookVersion, self.time_out))

        def about(self):
            method = "about"
            self.tracer.info("{0}.{1}() version {2}".format(self.__class__.__name__, method, fhSRHookVersion))
            return {"provider_company": "SUSE",
                    "provider_name": "SAPHanaSrTakeoverBlocker",  # class name
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
                # for test purposes just block all sr_takeover() calls
                tmp_file = tempfile.NamedTemporaryFile(prefix='SAPHanaSR_', suffix='_TBSRHOOK')
                cmd_out = tmp_file.name
                tmp_file.close()
                my_sid = os.environ.get('SAPSYSTEMNAME')
                low_sid = my_sid.lower()
                my_attribute = "hana_{0}_sra".format(low_sid)
                my_cmd = "sudo /usr/sbin/crm_attribute -n {0} -G -t reboot -q".format(my_attribute)
                self.tracer.info("{0}.{1}() my_cmd is: {2}, cmd_out is: {3}".format(self.__class__.__name__, method, my_cmd, cmd_out))
                my_sra = ""
                cmdrc = os.system(my_cmd + " > " + cmd_out)
                if cmdrc != 0:
                    # sr_takeover attribute not found or other problem
                    # block takeover
                    self.tracer.info("{0}.{1}() sr_takeover attribute not found, reject non-cluster action sr_takeover() - rc of my_cmd is {2} - runtime was ---{3} seconds ---".format(self.__class__.__name__, method, os.WEXITSTATUS(cmdrc), (time.time() - start_time)))
                    return RC_TOB

                # srtakeover attribute found, read values from file
                my_sra_res = ""
                try:
                    with open(cmd_out, 'r') as sra_file:
                        my_sra_res = sra_file.read()
                        sra_file.close()
                except (IOError, OSError) as err:
                    self.tracer.info("{0}.{1}() reading command output failed - {2}".format(self.__class__.__name__, method, err))
                os.remove(cmd_out)

                my_sra_lines = list(my_sra_res)
                for line in my_sra_lines:
                    my_sra = my_sra + line
                my_sra = my_sra.rstrip()
                if my_sra == "T":
                    self.tracer.info("{0}.{1}() permit cluster action sr_takeover() sra={2}".format(self.__class__.__name__, method, my_sra))
                    sra_rc = 0
                else:
                    tout_cmd = "timeout {0}s".format(self.time_out)
                    maint_cmd = "sudo /usr/sbin/SAPHanaSR-SRHhelper {0}".format(my_sid.upper())
                    self.tracer.info("{0}.{1}() maint_cmd is: {2}, tout_cmd is: {3}".format(self.__class__.__name__, method, maint_cmd, tout_cmd))
                    cmdrc = os.WEXITSTATUS(os.system(tout_cmd + " " + maint_cmd))
                    if cmdrc == 5:
                        # multi-state resource in maintenance, permit takeover
                        self.tracer.info("{0}.{1}() permit cluster action sr_takeover() sra={2}, but found cluster maintenance settings".format(self.__class__.__name__, method, my_sra))
                        sra_rc = 0
                    else:
                        # block takeover because
                        # timeout or multi-state resource NOT in maintenance
                        self.tracer.info("{0}.{1}() reject non-cluster action sr_takeover() sra={2}, cmdrc={3}".format(self.__class__.__name__, method, my_sra, cmdrc))
                        try:
                            sra_rc = self.errorCodeClusterConfigured  # take the correct rc from HANA settings
                        except:  # pylint: disable=bare-except
                            sra_rc = RC_TOB  # fallback for self.errorCodeClusterConfigured, if HANA does not already provide the rc codes

                self.tracer.info("{0}.{1}() leave postTakeover hook - rc is {2} - runtime was ---{3} seconds ---".format(self.__class__.__name__, method, sra_rc, (time.time() - start_time)))
                return sra_rc

            # possible force-takeover only code
            # usually nothing to do here
            self.tracer.info("{0}.{1}() leave postTakeover hook - runtime was ---{2} seconds ---".format(self.__class__.__name__, method, (time.time() - start_time)))
            return 0

except NameError as e:
    print("Could not find base class ({0})".format(e))
