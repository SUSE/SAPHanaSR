"""
# SAPHana
# Author:       Fabian Herschel, 2015
# License:      GNU General Public License (GPL)
# Copyright:    (c) 2015-2016 SUSE Linux GmbH
# Copyright:    (c) 2017-2022 SUSE LLC
"""
try:
    from hdb_ha_dr.client import HADRBase
except ImportError as e:
    print("Module HADRBase not found - running outside of SAP HANA? - {0}".format(e))
import os

"""
To use this HA/DR hook provide please add the following lines to your global.ini:
    [ha_dr_provider_susHanaSR]
    provider = susHanaSR
    path = /usr/share/SAPHanaSR-angi
    execution_order = 1

    [trace]
    ha_dr_saphanasr = info
"""
fhSRHookVersion = "1.000.0"


try:
    class susHanaSR(HADRBase):

        def __init__(self, *args, **kwargs):
            # delegate construction to base class
            super(susHanaSR, self).__init__(*args, **kwargs)
            self.tracer.info("susHanaSR init()") 

        def about(self):
            return {"provider_company": "SUSE",
                    "provider_name": "susHanaSR",  # class name
                    "provider_description": "Inform Cluster about SR state",
                    "provider_version": "1.0"}

        def srConnectionChanged(self, ParamDict, **kwargs):
            """ finally we got the srConnection hook :) """
            method = "srConnectionChanged"
            self.tracer.info("susHanaSR {0} {1}.srConnectionChanged method called with Dict={2}".format(fhSRHookVersion, self.__class__.__name__, ParamDict))
            # myHostname = socket.gethostname()
            # myDatebase = ParamDict["database"]
            mySystemStatus = ParamDict["system_status"]
            mySID = os.environ.get('SAPSYSTEMNAME')
            mysid = mySID.lower()
            myInSync = ParamDict["is_in_sync"]
            myReason = ParamDict["reason"]
            mySite = ParamDict["siteName"]
            self.tracer.info("susHanaSR {0}.srConnectionChanged mySystemStatus={1} mySID={2} myInSync={3} myReason={4}".format(self.__class__.__name__, mySystemStatus, mySID, myInSync, myReason))
            if mySystemStatus == 15:
                mySRS = "SOK"
            else:
                if myInSync:
                    # ignoring the SFAIL, because we are still in sync
                    self.tracer.info("susHanaSR (%s) %s.srConnectionChanged ignoring bad SR status because of is_in_sync=True (reason=%s)" % (fhSRHookVersion, self.__class__.__name__, myReason))
                    mySRS = ""
                else:
                    mySRS = "SFAIL"
            if mySRS == "":
                myMSG = "### Ignoring bad SR status because of is_in_sync=True ###"
                self.tracer.info("{0}.{1}() {2}\n".format(self.__class__.__name__, method, myMSG))
            elif mySite == "":
                myMSG = "### Ignoring bad SR status because of empty site name in call params ###"
                self.tracer.info("{0}.{1}() {2}\n".format(self.__class__.__name__, method, myMSG))
            else:
                myCMD = "sudo /usr/bin/crm_attribute -n hana_%s_site_srHook_%s -v %s -t crm_config -s SAPHanaSR" % (mysid, mySite, mySRS)
                rc = os.system(myCMD)
                myMSG = "CALLING CRM: <{0}> rc={1}".format(myCMD, rc)
                self.tracer.info("{0}.{1}() {2}\n".format(self.__class__.__name__, method, myMSG))
                if rc != 0:
                    #
                    # FALLBACK
                    # sending attribute to the cluster failed - using fallback method and write status to a file - RA to pick-up the value during next SAPHanaController monitor operation
                    #
                    myMSG = "sending attribute to the cluster failed - using local file as fallback"
                    self.tracer.info("{0}.{1}() {2}\n".format(self.__class__.__name__, method, myMSG))
                    #
                    # cwd of hana is /hana/shared/<SID>/HDB00/<hananode> we use a relative path to cwd this gives us a <sid>adm permitted directory
                    #     however we go one level up (..) to have the file accessible for all SAP HANA swarm nodes
                    #
                    fallbackFileObject = open("../.crm_attribute.stage.{0}".format(mySite), "w")
                    fallbackFileObject.write("hana_{0}_site_srHook_{1} = {2}".format(mysid, mySite, mySRS))
                    fallbackFileObject.close()
                    #
                    # release the stage file to the original name (move is used to be atomic)
                    #      .crm_attribute.stage.<site> is renamed to .crm_attribute.<site>
                    #
                    os.rename("../.crm_attribute.stage.{0}".format(mySite), "../.crm_attribute.{0}".format(mySite))
            return 0
except NameError as e:
    print("Could not find base class ({0})".format(e))
