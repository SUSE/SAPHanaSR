"""
# SAPHana
# Author:       Fabian Herschel, June 2022
# License:      GNU General Public License (GPL)
# Copyright:    (c) 2022 SUSE LLC

susChkSrv needs SAP HANA 2.0 SPS4 (2.00.040.00) as minimum version

To use this HA/DR hook provide please add the following lines (or similar) to your global.ini:
    [ha_dr_provider_suschksrv]
    provider = susChkSrv
    path = /usr/share/SAPHanaSR
    execution_order = 2

    [trace]
    ha_dr_suschksrv = info

"""

# loading classes and libraries
import os
import time

try:
    from hdb_ha_dr.client import HADRBase
except ImportError as e:
    print("Module HADRBase not found - running outside of SAP HANA? - {0}".format(e))

# hook section
SRHookName="susChkSrv"
SRHookVersion = "0.1.8"
# parameter section
TIME_OUT_DFLT = 30

try:
    class susChkSrv(HADRBase):

        def __init__(self, *args, **kwargs):
            # delegate construction to base class
            super(susChkSrv, self).__init__(*args, **kwargs)
            method = "init"

            # read settings from global.ini
            # read sustkover_timeout
            if self.config.hasKey("suschksrv_timeout"):
                self.time_out = self.config.get("suschksrv_timeout")
            else:
                self.time_out = TIME_OUT_DFLT
            if self.config.hasKey("suschksrv_action_on_lost"):
                self.action_on_lost = self.config.get("suschksrv_action_on_lost")
            else:
                self.action_on_lost = "ignore"
            self.tracer.info("{0}.{1}() version {2}, time_out {3} action_on_lost {4}".format(self.__class__.__name__, method, SRHookVersion, self.time_out, self.action_on_lost))

        def about(self):
            method = "about"
            self.tracer.info("{0}.{1}() version {2}".format(self.__class__.__name__, method, SRHookVersion))
            return {"provider_company": "SUSE",
                    "provider_name": "susChkSrv",  # class name
                    "provider_description": "Process service status changed events",
                    "provider_version": "1.0"}

        def srServiceStateChanged(self, ParamDict, **kwargs):
            method="srServiceStateChanged"
            mySID = os.environ.get('SAPSYSTEMNAME')
            self.tracer.info("{0} version {1}. Method {2} method called.".format(SRHookName, SRHookVersion, method))
            self.tracer.info("{0} {1} method called with Dict={2}".format(SRHookName, method, ParamDict))
            self.tracer.info("{0} {1} method called with SAPSYSTEMNAME={2}".format(SRHookName, method, mySID))
            # extract the 'central' values from the dictionary
            hostname = ParamDict['hostname']
            service = ParamDict['service_name']
            port = ParamDict['service_port']
            status = ParamDict['service_status']
            previousStatus = ParamDict['service_previous_status']
            timestamp = ParamDict['timestamp']
            daemonStatus = ParamDict['daemon_status']
            databaseId = ParamDict['database_id']
            databaseName = ParamDict['database_name']
            databaseStatus = ParamDict['database_status']

            # log service_name, service_port, service_status, service_previous_status,    database_id, database_name, database_status,    daemon_status
            self.tracer.info("srv:{0}-{1}-{2}-{3} db:{4}-{5}-{6} daem:{7}".format(service,port,status,previousStatus, databaseName,databaseId,databaseStatus, daemonStatus ))

            # analysis, if the event looks like an dying indexserver (LOST)
            isIndexserver = (service == "indexserver")
            serviceActive = (status == "yes" )
            serviceRestart = (status in ["starting", "stopping", "no"])
            serviceStop = (status in [ "stopping", "no"])
            serviceStopping = (status in [ "stopping"])
            serviceDown = (status == "no" )
            daemonActive = (daemonStatus == "yes")
            daemonStop = (daemonStatus == "stopping")
            daemonStarting = (daemonStatus == "starting")
            databaseActive = (databaseStatus == "yes")
            databaseStop = (databaseStatus == "stopping")

            eventKnown = False

            if ( isIndexserver and serviceRestart and daemonActive and databaseActive ) :
                self.tracer.info("LOST: indexserver event looks like a lost indexserver")
                eventKnown = True
            if ( isIndexserver and serviceActive and daemonActive and databaseActive ) :
                self.tracer.info("LOST: indexserver event looks like a lost indexserver (indexserver started)")
                eventKnown = True
            if ( isIndexserver and serviceStopping and daemonStop ) :
                self.tracer.info("STOP: indexserver event looks like graceful instance stop")
                eventKnown = True
            if ( isIndexserver and serviceDown and daemonStop ) :
                self.tracer.info("STOP: indexserver event looks like graceful instance stop (indexserver stopped)")
                eventKnown = True
            if ( isIndexserver and serviceStopping and daemonActive and databaseStop ) :
                self.tracer.info("DOWN: indexserver event looks like graceful tenant stop")
                eventKnown = True
            if ( isIndexserver and serviceDown and daemonActive and databaseStop ) :
                self.tracer.info("DOWN: indexserver event looks like graceful tenant stop (indexserver stopped)")
                eventKnown = True
            if ( isIndexserver and serviceRestart and daemonStarting and databaseActive ) :
                self.tracer.info("START: indexserver event looks like graceful tenant start")
                eventKnown = True
            if ( isIndexserver and serviceActive and daemonStarting and databaseActive ) :
                self.tracer.info("START: indexserver event looks like graceful tenant start (indexserver started)")
                eventKnown = True
            if ( isIndexserver and not eventKnown ) :
                self.tracer.info("DBG: version={},serviceRestart={}, serviceStop={}, serviceDown={}, daemonActive={}, daemonStop={}, daemonStarting={}, databaseActive={}, databaseStop={}".format(SRHookVersion, serviceRestart,serviceStop,serviceDown,daemonActive,daemonStop,daemonStarting,databaseActive,databaseStop))
            return 0

except NameError as e:
    print("Could not find base class ({0})".format(e))
