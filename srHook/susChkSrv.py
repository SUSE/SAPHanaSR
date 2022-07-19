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
    action_on_lost = kill | stop | ignore (fence and attr currently not implemented)
    stop_timeout = 20
    # timeout = timeout-in-seconds (currently not implemented)

    [trace]
    ha_dr_suschksrv = info

TODO: Do we also want this hook to jump-in, if a secondary indexserver is crashing? Maybe to be selected by a parameter.
TODO: The hook might not do it's action, if the SR is not-in-sync. Maybe to be selected by a parameter
TODO: actions "fence", "attr" (attr is to inform the cluster (RA) to handle this SAP instance as broken)
TODO: action "kill". The hard-coded sleep 5 is to allow the nameserver to log events. To be checked, if 5s is a good sleep time. Maybe to be tuned by a parameter
TODO: To be tested with "real"  slow dying indexservers
TODO: action "kill" is only valid for Scale-Up and might break on SAP HANA instances with tenants and high-isolation (different linux users per tenant)

"""

# loading classes and libraries
import os
import time
import random
from datetime import datetime

try:
    from hdb_ha_dr.client import HADRBase
    import ConfigMgrPy
except ImportError as e:
    print("Module HADRBase not found - running outside of SAP HANA? - {0}".format(e))

# hook section
SRHookName="susChkSrv"
SRHookVersion = "0.3.3"
# parameter section
TIME_OUT_DFLT = 20

def getEpisode():
    episode = "{0}-{1}".format( datetime.now().strftime('%s') , random.randrange(10000,20000))
    return episode

def logTimestamp(episode, outputMessage):
    traceFilepath = os.path.join(os.environ['SAP_RETRIEVAL_PATH'], 'trace', 'nameserver_suschksrv.trc')
    try:
        with open(traceFilepath, "a") as saphanasr_multitarget_file:
            currentTimeStr = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f ')
            outputMessage = "{0} [{2}] {1}".format(currentTimeStr,outputMessage, episode)
            saphanasr_multitarget_file.write(outputMessage + "\n")
            saphanasr_multitarget_file.flush()

    except ( RuntimeError, TypeError, NameError, OSError ) as e :
        self.tracer.info("{0}.{1}() logTimestamp error {2}".format(self.__class__.__name__, method, e))
        print("Error in logTimestamp(): {0}".format(e))

try:
    class susChkSrv(HADRBase):

        def __init__(self, *args, **kwargs):
            # delegate construction to base class
            super(susChkSrv, self).__init__(*args, **kwargs)
            method = "init"
            episode = getEpisode()
            logTimestamp(episode, "init called")

            # read settings from global.ini
            # read sustkover_timeout
            if self.config.hasKey("stop_timeout"):
                self.stop_timeout = self.config.get("stop_timeout")
            else:
                self.stop_timeout = TIME_OUT_DFLT
            if self.config.hasKey("action_on_lost"):
                self.action_on_lost = self.config.get("action_on_lost")
                isValidAction = ( self.action_on_lost in ["ignore", "fence", "kill", "stop", "attr"] )
                if ( not (isValidAction )):
                    self.tracer.info("Invalid action_on_lost {}. Fallback to ignore".format(self.action_on_lost))
                    self.action_on_lost = "ignore_fallback"
            else:
                self.tracer.info("action_on_lost not configured. Fallback to ignore".format())
                self.action_on_lost = "ignore_default"
            self.tracer.info("{0}.{1}() version {2}, parameter info: stop_timeout={3} action_on_lost={4}".format(self.__class__.__name__, method, SRHookVersion, self.stop_timeout, self.action_on_lost))
            # TODO: use action specific init messages (e.g. for stop also report stop_timeout)
            self.takeover_active = False
            self.ino = ConfigMgrPy.sapgparam('SAPSYSTEM')

        def about(self):
            method = "about"
            self.tracer.info("{0}.{1}() version {2}".format(self.__class__.__name__, method, SRHookVersion))
            return {"provider_company": "SUSE",
                    "provider_name": "susChkSrv",  # class name
                    "provider_description": "Process service status changed events",
                    "provider_version": "1.0"}

        def preTakeover(self, isForce, **kwargs):
            self.takeover_active = True
            self.tracer.info("DBG: version={} preTakeover - set takeover_active = True".format(SRHookVersion))
            # TODO: what about "blocked" takeovers? Test-Result: In a blocked takeover situation, postTakeover() is not called
            return 0;

        def postTakeover(self, isForce, **kwargs):
            self.takeover_active = False
            self.tracer.info("DBG: version={} postTakeover - set takeover_active = False".format(SRHookVersion))
            return 0;

        def srServiceStateChanged(self, ParamDict, **kwargs):
            method="srServiceStateChanged"
            mySID = os.environ.get('SAPSYSTEMNAME')
            episode = getEpisode()
            self.tracer.info("{0} version {1}. Method {2} method called.".format(SRHookName, SRHookVersion, method))
            self.tracer.info("{0} {1} method called with Dict={2}".format(SRHookName, method, ParamDict))
            self.tracer.info("{0} {1} method called with SAPSYSTEMNAME={2}".format(SRHookName, method, mySID))
            logTimestamp(episode, "{} version {}. Method {} method called.".format(SRHookName, SRHookVersion, method))
            logTimestamp(episode, "{} {} method called with Dict={}".format(SRHookName, method, ParamDict))
            logTimestamp(episode, "{} {} method called with SAPSYSTEMNAME={} instanceNumber={}".format(SRHookName, method, mySID, self.ino))
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
            isLostIndexserver = False

            if ( isIndexserver and serviceRestart and daemonActive and databaseActive ) :
                self.tracer.info("LOST: indexserver event looks like a lost indexserver")
                logTimestamp(epsiode, "LOST: indexserver event looks like a lost indexserver")
                isLostIndexserver = True
                eventKnown = True
            if ( isIndexserver and serviceActive and daemonActive and databaseActive ) :
                if ( self.takeover_active ):
                    self.tracer.info("TAKEOVER: indexserver event looks like a takeover event")
                    logTimestamp(epsiode, "TAKEOVER: indexserver event looks like a takeover event")
                else:
                    self.tracer.info("LOST: indexserver event looks like a lost indexserver (indexserver started)")
                    logTimestamp(epsiode, "LOST: indexserver event looks like a lost indexserver (indexserver started)")
                eventKnown = True
                # TODO: this event (LOST/started) seems also to come, if a sr_takeover is been processed (using preTakeover() and postTakeover() to mark this event?)
            if ( isIndexserver and serviceStopping and daemonStop ) :
                self.tracer.info("STOP: indexserver event looks like graceful instance stop")
                logTimestamp(epsiode, "STOP: indexserver event looks like graceful instance stop")
                eventKnown = True
            if ( isIndexserver and serviceDown and daemonStop ) :
                self.tracer.info("STOP: indexserver event looks like graceful instance stop (indexserver stopped)")
                logTimestamp(epsiode, "STOP: indexserver event looks like graceful instance stop (indexserver stopped)")
                eventKnown = True
            if ( isIndexserver and serviceStopping and daemonActive and databaseStop ) :
                self.tracer.info("DOWN: indexserver event looks like graceful tenant stop")
                logTimestamp(epsiode, "DOWN: indexserver event looks like graceful tenant stop")
                eventKnown = True
            if ( isIndexserver and serviceDown and daemonActive and databaseStop ) :
                self.tracer.info("DOWN: indexserver event looks like graceful tenant stop (indexserver stopped)")
                logTimestamp(epsiode, "DOWN: indexserver event looks like graceful tenant stop (indexserver stopped)")
                eventKnown = True
            if ( isIndexserver and serviceRestart and daemonStarting and databaseActive ) :
                self.tracer.info("START: indexserver event looks like graceful tenant start")
                logTimestamp(epsiode, "START: indexserver event looks like graceful tenant start")
                eventKnown = True
            if ( isIndexserver and serviceActive and daemonStarting and databaseActive ) :
                self.tracer.info("START: indexserver event looks like graceful tenant start (indexserver started)")
                logTimestamp(epsiode, "START: indexserver event looks like graceful tenant start (indexserver started)")
                eventKnown = True
            if ( isIndexserver and not eventKnown ) :
                self.tracer.info("DBG: version={},serviceRestart={}, serviceStop={}, serviceDown={}, daemonActive={}, daemonStop={}, daemonStarting={}, databaseActive={}, databaseStop={}".format(SRHookVersion, serviceRestart,serviceStop,serviceDown,daemonActive,daemonStop,daemonStarting,databaseActive,databaseStop))
                logTimestamp(epsiode, "DBG: version={},serviceRestart={}, serviceStop={}, serviceDown={}, daemonActive={}, daemonStop={}, daemonStarting={}, databaseActive={}, databaseStop={}".format(SRHookVersion, serviceRestart,serviceStop,serviceDown,daemonActive,daemonStop,daemonStarting,databaseActive,databaseStop))
            # event on secondary, if HA1 tenant is stopped on primary
            # DBG: version=0.2.7,serviceRestart=True, serviceStop=True, serviceDown=False, daemonActive=True, daemonStop=False, daemonStarting=False, databaseActive=False, databaseStop=False
            # DBG: version=0.2.7,serviceRestart=True, serviceStop=True, serviceDown=True, daemonActive=True, daemonStop=False, daemonStarting=False, databaseActive=False, databaseStop=False


            #
            # doing the action
            #
            if ( isLostIndexserver and ( self.action_on_lost in [ "ignore", "ignore_fallback", "ignore_default" ] )):
                self.tracer.info("LOST: event ignored. action_on_lost={}".format(self.action_on_lost))
     
            if ( isLostIndexserver and ( self.action_on_lost == "fence" )):
                self.tracer.info("LOST: fence node. action_on_lost={}".format(self.action_on_lost))
                self.tracer.info("LOST: action_on_lost={} is currently not implemented".format(self.action_on_lost))
                logTimestamp(epsiode, "LOST: fence node. action_on_lost=fence is currently not implemented")
                # TODO add fence code here
            if ( isLostIndexserver and ( self.action_on_lost == "kill" )):
                self.tracer.info("LOST: kill instance. action_on_lost={}".format(self.action_on_lost))
                logTimestamp(epsiode, "LOST: kill instance. action_on_lost={}".format(self.action_on_lost))
                tout_cmd=""
                action_cmd = "HDB kill-{}".format("9")
                # doing a short sleep before killing all SAP HANA processes to allow nameserver to write the already sent log messages
                cmdrc = os.WEXITSTATUS(os.system("sleep {}; {} {}".format("5", tout_cmd, action_cmd )))
                logTimestamp(epsiode, "LOST: killed instance. action_on_lost={}".format(self.action_on_lost))
                # TODO: hadcoded 5 here to be moved to a self.sleep_before_action (or however it will be named)
            if ( isLostIndexserver and ( self.action_on_lost == "stop" )):
                self.tracer.info("LOST: stop instance. action_on_lost={}".format(self.action_on_lost))
                logTimestamp(epsiode, "LOST: stop instance. action_on_lost={}".format(self.action_on_lost))
                tout_cmd="timeout {}".format(self.stop_timeout)
                action_cmd = "HDB stop"
                cmdrc = os.WEXITSTATUS(os.system("sleep {}; {} {}".format( "5", tout_cmd, action_cmd )))
                # TODO HDB stop is only valid for Scale-Up but does not need the instance number
            if ( isLostIndexserver and ( self.action_on_lost == "attr" )):
                self.tracer.info("LOST: set cluster attribute. action_on_lost={}".format(self.action_on_lost))
                self.tracer.info("LOST: action_on_lost={} is currently not implemented".format(self.action_on_lost))
                logTimestamp(epsiode, "LOST: attr node. action_on_lost=attr is currently not implemented")
                # TODO add attribute code here
            return 0

except NameError as e:
    print("Could not find base class ({0})".format(e))
