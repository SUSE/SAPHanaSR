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
    execution_order = 1

    [trace]
    ha_dr_saphanasrtakeoverblocker = info

"""

# loading classes and libraries
import os
import tempfile

try:
    from hdb_ha_dr.client import HADRBase
except ImportError as e:
    print("Module HADRBase not found - running outside of SAP HANA? - {0}".format(e))

# parameter section
fhSRHookVersion = "0.160.1"

try:
    class SAPHanaSrTakeoverBlocker(HADRBase):

        def __init__(self, *args, **kwargs):
            # delegate construction to base class
            super(SAPHanaSrTakeoverBlocker, self).__init__(*args, **kwargs)
            method = "init"
            self.tracer.info("{0}.{1}() version {2}".format(self.__class__.__name__, method, fhSRHookVersion))

        def about(self):
            method = "about"
            self.tracer.info("{0}.{1}() version {2}".format(self.__class__.__name__, method, fhSRHookVersion))
            return {"provider_company": "SUSE",
                    "provider_name": "SAPHanaSrTakeoverBlocker",  # class name
                    "provider_description": "Inform Cluster about SR state",
                    "provider_version": "1.0"}

        def startup(self, hostname, storage_partition, sr_mode, **kwargs):
            method = "startup"
            self.tracer.debug("enter startup hook; {0}".format(locals()))
            self.tracer.debug(self.config.toString())
            self.tracer.info("leave startup hook")
            return 0

        def shutdown(self, hostname, storage_partition, sr_mode, **kwargs):
            method = "shutdown"
            self.tracer.debug("enter shutdown hook; {0}".format(locals()))
            self.tracer.debug(self.config.toString())
            self.tracer.info("leave shutdown hook")
            return 0

        def failover(self, hostname, storage_partition, sr_mode, **kwargs):
            method = "failover"
            self.tracer.debug("enter failover hook; {0}".format(locals()))
            self.tracer.debug(self.config.toString())
            self.tracer.info("leave failover hook")
            return 0

        def stonith(self, failingHost, **kwargs):
            method = "stonith"
            self.tracer.debug("enter stonith hook; {0}".format(locals()))
            self.tracer.debug(self.config.toString())
            # e.g. stonith of params["failed_host"]
            # e-g- set vIP active
            self.tracer.info("leave stonith hook")
            return 0

        def preTakeover(self, isForce, **kwargs):
            """Pre takeover hook."""
            """
               * TODO PRIO1: add check, if cluster does actively manage the resource
               * Prerequisites:
               *    RA does set the same attribute as checked here (key and value)
               *    Sudoers does allow the query of the attribute (alternatively add <sid>adm user(s) to hacluster group)
            """
            method = "preTakeover"
            self.tracer.info("{0}.{1}() called with isForce={2}".format(self.__class__.__name__, method, isForce))
            if not isForce:
                # run pre takeover code
                # run pre-check, return != 0 in case of error => will abort takeover
                # for test purposes just block all sr_takeover() calls
                tmpFile = tempfile.NamedTemporaryFile(prefix='SAPHanaSR_', suffix='_TBSRHOOK')
                cmdOut = tmpFile.name
                tmpFile.close()
                mySID = os.environ.get('SAPSYSTEMNAME')
                mysid = mySID.lower()
                myAttribute = "hana_{0}_sra".format(mysid)
                myCMD = "sudo /usr/sbin/crm_attribute -n {0} -G -t reboot -q".format(myAttribute)
                self.tracer.info("{0}.{1}() myCMD is: {2}, cmdOut is: {3}".format(self.__class__.__name__, method, myCMD, cmdOut))
                mySRA = ""
                rc = os.system(myCMD + " > " + cmdOut)
                if rc != 0:
                    # srtakeover attribute not found
                    return 0

                # srtakeover attribute found, read values from file
                mySRAres = ""
                with open(cmdOut, 'r') as sraFile:
                    mySRAres = sraFile.read()
                    sraFile.close()
                os.remove(cmdOut)

                mySRAlines = list(mySRAres)
                for line in mySRAlines:
                    mySRA = mySRA + line
                mySRA = mySRA.rstrip()
                if mySRA == "T":
                    self.tracer.info("{0}.{1}() permit cluster action sr_takeover() sra={2}".format(self.__class__.__name__, method, mySRA))
                    rc = 0
                else:
                    self.tracer.info("{0}.{1}() reject non-cluster action sr_takeover() sra={2}".format(self.__class__.__name__, method, mySRA))
                    try:
                        rc = self.errorCodeClusterConfigured  # take the correct rc from HANA settings
                    except:  # pylint: disable=bare-except
                        rc = 50277  # fallback for self.errorCodeClusterConfigured, if HANA does not already provide the rc codes
                return rc

            # possible force-takeover only code
            # usually nothing to do here
            return 0

        def postTakeover(self, rc, **kwargs):
            """Post takeover hook."""
            method = "postTakeover"
            self.tracer.info("{0}.{1}() method called with rc={2}".format(self.__class__.__name__, method, rc))
            if rc == 0:
                # normal takeover succeeded
                return 0
            elif rc == 1:
                # waiting for force takeover
                return 0
            elif rc == 2:
                # error, something went wrong
                return 0

        def srConnectionChanged(self, ParamDict, **kwargs):
            """ This hook should just do nothing for this HA/DR method """
            method = "srConnectionChanged"
            self.tracer.info("{0}.{1}() method called".format(self.__class__.__name__, method))
            return 0
except NameError as e:
    print("Could not find base class ({0})".format(e))
