from hdb_ha_dr.client import HADRBase
import os

"""
Sample for a HA/DR hook provider.
When using your own code in here, please copy this file to location on
/hana/shared outside the HANA installation.
To use this HA/DR hook provide please add the following lines (or
similar) to your global.ini:
    [ha_dr_provider_SAPHanaSR]
    provider = SAPHanaSR
    path = /hana/shared/myHooks/SAPHanaSR-ScaleOut
    execution_order = 1

    [trace]
    ha_dr_saphanasr = info
"""
fhSRHookVersion = "0.161.0"


class SAPHanaSR(HADRBase):

    def __init__(self, *args, **kwargs):
        # delegate construction to base class
        super(SAPHanaSR, self).__init__(*args, **kwargs)

    def about(self):
        return {"provider_company": "SUSE",
                "provider_name": "SAPHanaSR",  # class name
                "provider_description": "Inform Cluster about SR state",
                "provider_version": "1.0"}

    def startup(self, hostname, storage_partition, sr_mode, **kwargs):
        self.tracer.debug("enter startup hook; %s" % locals())
        self.tracer.debug(self.config.toString())
        self.tracer.info("leave startup hook")
        return 0

    def shutdown(self, hostname, storage_partition, sr_mode, **kwargs):
        self.tracer.debug("enter shutdown hook; %s" % locals())
        self.tracer.debug(self.config.toString())
        self.tracer.info("leave shutdown hook")
        return 0

    def failover(self, hostname, storage_partition, sr_mode, **kwargs):
        self.tracer.debug("enter failover hook; %s" % locals())
        self.tracer.debug(self.config.toString())
        self.tracer.info("leave failover hook")
        return 0

    def stonith(self, failingHost, **kwargs):
        self.tracer.debug("enter stonith hook; %s" % locals())
        self.tracer.debug(self.config.toString())
        # e.g. stonith of params["failed_host"]
        # e-g- set vIP active
        self.tracer.info("leave stonith hook")
        return 0

    def preTakeover(self, isForce, **kwargs):
        """Pre takeover hook."""
        self.tracer.info("%s.preTakeover method called with isForce=%s" % (self.__class__.__name__, isForce))
        if not isForce:
            # run pre takeover code
            # run pre-check, return != 0 in case of error => will abort takeover
            return 0
        else:
            # possible force-takeover only code
            # usually nothing to do here
            return 0

    def postTakeover(self, rc, **kwargs):
        """Post takeover hook."""
        self.tracer.info("%s.postTakeover method called with rc=%s" % (self.__class__.__name__, rc))
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
        """ finally we got the srConnection hook :) """
        self.tracer.info("SAPHanaSR (%s) %s.srConnectionChanged method called with Dict=%s" % (fhSRHookVersion, self.__class__.__name__, ParamDict))
        # myHostname = socket.gethostname()
        # myDatebase = ParamDict["database"]
        mySystemStatus = ParamDict["system_status"]
        mySID = os.environ.get('SAPSYSTEMNAME')
        mysid = mySID.lower()
        myInSync = ParamDict["is_in_sync"]
        myReason = ParamDict["reason"]
        mySite = ParamDict["siteName"]
        if (mySystemStatus == 15):
            mySRS = "SOK"
        else:
            if (myInSync):
                # ignoring the SFAIL, because we are still in sync
                self.tracer.info("SAPHanaSR (%s) %s.srConnectionChanged ignoring bad SR status because of is_in_sync=True (reason=%s)" % (fhSRHookVersion, self.__class__.__name__, myReason))
                mySRS = ""
            else:
                mySRS = "SFAIL"
        if (mySRS == ""):
            self.tracer.info("SAPHanaSR (%s) 001" % (self.__class__.__name__))
            myMSG = "### Ignoring bad SR status because of is_in_sync=True ###"
            self.tracer.info("SAPHanaSR (%s) 002" % (self.__class__.__name__))
        else:
            myCMD = "sudo /usr/sbin/crm_attribute -n hana_%s_site_srHook_%s -v %s -t crm_config -s SAPHanaSR" % (mysid, mySite, mySRS)
            rc = os.system(myCMD)
            myMSG = "CALLING CRM: <" + myCMD + "> rc=" + str(rc)
        self.tracer.info("SAPHanaSR %s.srConnectionChanged method called with Dict=%s ###\n" % (self.__class__.__name__, ParamDict))
        self.tracer.info("SAPHanaSR %s \n" % (myMSG))
        return 0
