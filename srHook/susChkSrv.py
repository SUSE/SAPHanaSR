# pylint: disable=invalid-name,fixme
"""
# susChkSrv.py
# Author:       Fabian Herschel, June 2022
# License:      GNU General Public License (GPL)
# Copyright:    (c) 2022 SUSE LLC

susChkSrv needs SAP HANA 2.0 SPS4 (2.00.040.00) as minimum version

To use this HA/DR hook provide please add the following lines (or similar) to your global.ini:
    [ha_dr_provider_suschksrv]
    provider = susChkSrv
    path = /usr/share/SAPHanaSR
    execution_order = 2
    action_on_lost = kill | stop | ignore | fence (attr is currently not implemented)
    stop_timeout = 20
    # timeout = timeout-in-seconds (currently not implemented)

    [trace]
    ha_dr_suschksrv = info

TODO: Do we also want this hook to jump-in, if a secondary indexserver is crashing? Maybe to be
      selected by a parameter.
TODO: The hook might not do it's action, if the SR is not-in-sync. Maybe to be selected by a
      parameter
TODO: action "attr" (attr is to inform the cluster (RA) to handle this SAP instance
      as broken - maybe the project will not implement this as the other actions are 
      already sufficient)
TODO: action "kill". The hard-coded sleep 5 is to allow the nameserver to log events. To be
      checked, if 5s is a good sleep time. Maybe to be tuned by a parameter
TODO: To be tested with "real"  slow dying indexservers
TODO: action "kill" is only valid for Scale-Up and might break on SAP HANA instances with
      tenants and high-isolation (different linux users per tenant)
"""

# loading classes and libraries
import os
# import time
import random
from datetime import datetime

# XXpylint: enable=invalid-name
try:
    from hdb_ha_dr.client import HADRBase
    import ConfigMgrPy
except ImportError as e:
    print(f"Module HADRBase not found - running outside of SAP HANA? - {e}")

# hook section
SRHookName = "susChkSrv"
SRHookVersion = "1.001.1"
# parameter section
TIME_OUT_DFLT = 20


def getEpisode():
    """ get the episode string """
    episode = f"{datetime.now().strftime('%s')}-{random.randrange(10000, 20000)}"
    return episode




try:
    class susChkSrv(HADRBase):
        """ class for HADR hook script to handle service changed status events """

        def logTimestamp(self, method, episode, outputMessage):
            """ write message to log file with timestamp """
            traceFilepath = os.path.join(os.environ['SAP_RETRIEVAL_PATH'], 'trace',
                                         'nameserver_suschksrv.trc')
            try:
                with open(traceFilepath, "a", encoding="UTF-8") as saphanasr_multitarget_file:
                    currentTimeStr = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f ')
                    outputMessage = f"{currentTimeStr} [{episode}] {outputMessage}"
                    saphanasr_multitarget_file.write(outputMessage + "\n")
                    saphanasr_multitarget_file.flush()
            except (RuntimeError, TypeError, NameError, OSError) as err:
                self.tracer.info(f"{self.__class__.__name__}.{method}() logTimestamp error {err}")
                print(f"Error in logTimestamp(): {err}")

        def __init__(self, *args, **kwargs):
            # delegate construction to base class
            super().__init__(*args, **kwargs)
            method = "init"
            episode = getEpisode()
            self.logTimestamp(method, episode, "init called")

            # read settings from global.ini
            # read sustkover_timeout
            if self.config.hasKey("stop_timeout"):
                self.stop_timeout = self.config.get("stop_timeout")
            else:
                self.stop_timeout = TIME_OUT_DFLT
            if self.config.hasKey("action_on_lost"):
                self.action_on_lost = self.config.get("action_on_lost")
                isValidAction = (self.action_on_lost in ["ignore", "fence", "kill", "stop",
                                 "firstStopThenKill"])
                if not isValidAction:
                    msg = f"Invalid action_on_lost {self.action_on_lost}. Fallback to 'ignore'"
                    self.logTimestamp(method, episode, msg)
                    self.tracer.info(msg)
                    self.action_on_lost = "ignore_fallback"
            else:
                msg = "action_on_lost not configured. Fallback to 'ignore'"
                self.logTimestamp(method, episode, msg)
                self.tracer.info(msg)
                self.action_on_lost = "ignore_default"
            if self.config.hasKey("kill_signal"):
                self.killSignal = self.config.get("kill_signal")
            else:
                self.killSignal = "9"
            # TODO: logging the signal parameter, but only if it is the kill action
            msg = (f"{self.__class__.__name__}.{method}() version {SRHookVersion}, parameter"
                   f" info: action_on_lost={self.action_on_lost} stop_timeout={self.stop_timeout}"
                   f" kill_signal={self.killSignal}")
            self.logTimestamp(method, episode, msg)
            self.tracer.info(msg)
            # TODO: use action specific init messages (e.g. for stop also report stop_timeout)
            self.takeover_active = False
            self.ino = ConfigMgrPy.sapgparam('SAPSYSTEM')

        def about(self):
            """ tell something about the HADR hook script """
            method = "about"
            self.tracer.info(f"{self.__class__.__name__}.{method}() version {SRHookVersion}")
            return {"provider_company": "SUSE",
                    "provider_name": "susChkSrv",  # class name
                    "provider_description": "Process service status changed events",
                    "provider_version": "1.0"}

        # pylint: disable-next=unused-argument
        def preTakeover(self, isForce, **kwargs):
            """ method to catch preTakeover events """
            self.takeover_active = True
            self.tracer.info(f"DBG: version={SRHookVersion} preTakeover"
                             " - set takeover_active = True")
            # TODO: what about "blocked" takeovers?
            # Test-Result: In a blocked takeover situation, postTakeover() is not called
            return 0

        # pylint: disable-next=unused-argument
        def postTakeover(self, isForce, **kwargs):
            """ method to catch postTakeover events """
            self.takeover_active = False
            self.tracer.info(f"DBG: version={SRHookVersion} postTakeover"
                             " - set takeover_active = False")
            return 0

        # pylint: disable-next=too-many-statements,too-many-locals,too-many-branches,unused-argument
        def srServiceStateChanged(self, ParamDict, **kwargs):
            """ method to catch srServiceStateChanged events """
            method = "srServiceStateChanged"
            mySID = os.environ.get('SAPSYSTEMNAME')
            episode = getEpisode()
            msg1 = f"{SRHookName} version {SRHookVersion}. Method {method} method called."
            msg2 = f"{SRHookName} {method} method called with Dict={ParamDict}"
            msg3 = f"{SRHookName} {method} method called with SAPSYSTEMNAME={mySID}"
            self.logTimestamp(method, episode, msg1)
            self.logTimestamp(method, episode, msg2)
            self.logTimestamp(method, episode, msg3)
            self.tracer.info(msg1)
            self.tracer.info(msg2)
            self.tracer.info(msg3)
            # extract the 'central' values from the dictionary
            # hostname = ParamDict['hostname']
            service = ParamDict['service_name']
            port = ParamDict['service_port']
            status = ParamDict['service_status']
            previousStatus = ParamDict['service_previous_status']
            # timestamp = ParamDict['timestamp']
            daemonStatus = ParamDict['daemon_status']
            databaseId = ParamDict['database_id']
            databaseName = ParamDict['database_name']
            databaseStatus = ParamDict['database_status']
            msg = (f"srv:{service}-{port}-{status}-{previousStatus}"
                   f" db:{databaseName}-{databaseId}-{databaseStatus} daem:{daemonStatus}")
            self.logTimestamp(method, episode, msg)
            self.tracer.info(msg)

            # analysis, if the event looks like an dying indexserver (LOST)
            isIndexserver = service == "indexserver"
            serviceActive = status == "yes"
            serviceRestart = status in ["starting", "stopping", "no"]
            serviceStop = status in ["stopping", "no"]
            serviceStopping = status in ["stopping"]
            serviceDown = status == "no"
            daemonActive = daemonStatus == "yes"
            daemonStop = daemonStatus == "stopping"
            daemonStarting = daemonStatus == "starting"
            databaseActive = databaseStatus == "yes"
            databaseStop = databaseStatus == "stopping"

            eventKnown = False
            isLostIndexserver = False

            #
            # TODO: Do we need to filter-out events with status=="starting"
            #       and previousStatus=="starting" ?
            #
            if (isIndexserver and serviceRestart and daemonActive and databaseActive):
                msg = f"LOST: indexserver event looks like a lost indexserver (status={status})"
                self.logTimestamp(method, episode, msg)
                self.tracer.info(msg)
                isLostIndexserver = True
                eventKnown = True
            if (isIndexserver and serviceActive and daemonActive and databaseActive):
                if self.takeover_active:
                    msg = "TAKEOVER: indexserver event looks like a takeover event"
                    self.logTimestamp(method, episode, msg)
                    self.tracer.info(msg)
                else:
                    msg = ("LOST: indexserver event looks like a lost indexserver"
                           " (indexserver started)")
                    self.logTimestamp(method, episode, msg)
                    self.tracer.info(msg)
                eventKnown = True
                # TODO: this event (LOST/started) seems also to come, if a sr_takeover is been
                #       processed (using preTakeover() and postTakeover() to mark this event?)
            if (isIndexserver and serviceStopping and daemonStop):
                msg = "STOP: indexserver event looks like graceful instance stop"
                self.logTimestamp(method, episode, msg)
                self.tracer.info(msg)
                eventKnown = True
            if (isIndexserver and serviceDown and daemonStop):
                msg = ("STOP: indexserver event looks like graceful instance stop"
                       " (indexserver stopped)")
                self.tracer.info(msg)
                self.logTimestamp(method, episode, msg)
                eventKnown = True
            if (isIndexserver and serviceStopping and daemonActive and databaseStop):
                msg = "STOP: indexserver event looks like graceful tenant stop"
                self.logTimestamp(method, episode, msg)
                self.tracer.info(msg)
                eventKnown = True
            if (isIndexserver and serviceDown and daemonActive and databaseStop):
                msg = ("STOP: indexserver event looks like graceful tenant stop"
                       " (indexserver stopped)")
                self.logTimestamp(method, episode, msg)
                self.tracer.info(msg)
                eventKnown = True
            if (isIndexserver and serviceRestart and daemonStarting and databaseActive):
                msg = "START: indexserver event looks like graceful tenant start"
                self.logTimestamp(method, episode, msg)
                self.tracer.info(msg)
                eventKnown = True
            if (isIndexserver and serviceActive and daemonStarting and databaseActive):
                msg = ("START: indexserver event looks like graceful tenant start"
                       " (indexserver started)")
                self.logTimestamp(method, episode, msg)
                self.tracer.info(msg)
                eventKnown = True
            if (isIndexserver and not eventKnown):
                msg = (f"DBG: version={SRHookVersion},serviceRestart={serviceRestart},"
                       f" serviceStop={serviceStop}, serviceDown={serviceDown},"
                       f" daemonActive={daemonActive}, daemonStop={daemonStop},"
                       f" daemonStarting={daemonStarting},"
                       f" databaseActive={databaseActive}, databaseStop={databaseStop}")
                self.logTimestamp(method, episode, msg)
                self.tracer.info(msg)
            # event on secondary, if HA1 tenant is stopped on primary
            # DBG: version=0.2.7,serviceRestart=True, serviceStop=True, serviceDown=False,
            #     daemonActive=True, daemonStop=False, daemonStarting=False, databaseActive=False,
            #     databaseStop=False
            # DBG: version=0.2.7,serviceRestart=True, serviceStop=True, serviceDown=True,
            #     daemonActive=True, daemonStop=False, daemonStarting=False, databaseActive=False,
            #     databaseStop=False

            #
            # doing the action
            #
            # pylint: disable-next=line-too-long
            if (isLostIndexserver and (self.action_on_lost in ["ignore", "ignore_fallback", "ignore_default"])):
                msg = f"LOST: event ignored. action_on_lost={self.action_on_lost}"
                self.logTimestamp(method, episode, msg)
                self.tracer.info(msg)
            if (isLostIndexserver and self.action_on_lost == "fence"):
                msg = f"LOST: fence node. action_on_lost={self.action_on_lost}"
                self.logTimestamp(method, episode, msg)
                self.tracer.info(msg)
                tout_cmd = ""
                action_cmd = f"sudo /usr/bin/SAPHanaSR-hookHelper --sid={mySID} --case=fenceMe"
                os.WEXITSTATUS(os.system(f"sleep 5; {tout_cmd} {action_cmd}"))
            if (isLostIndexserver and self.action_on_lost == "kill"):
                msg = (f"LOST: kill instance. action_on_lost={self.action_on_lost}"
                       f" signal={self.killSignal}")
                self.logTimestamp(method, episode, msg)
                self.tracer.info(msg)
                tout_cmd = ""
                action_cmd = f"HDB kill-{self.killSignal}"
                # doing a short sleep before killing all SAP HANA processes to allow nameserver
                # to write the already sent log messages
                os.WEXITSTATUS(os.system(f"sleep 5; {tout_cmd} {action_cmd}"))
                # the following message will most-likely also be lost, if we use signal 9
                msg = f"LOST: killed instance. action_on_lost={self.action_on_lost}"
                self.logTimestamp(method, episode, msg)
                # DONE: hardcoded 5 here to be moved to a self.sleep_before_action
                #       (or however it will be named)
            if (isLostIndexserver and self.action_on_lost == "stop"):
                msg = f"LOST: stop instance. action_on_lost={self.action_on_lost}"
                self.logTimestamp(method, episode, msg)
                self.tracer.info(msg)
                tout_cmd = f"timeout {self.stop_timeout}"
                # action_cmd = "HDB stop"
                action_cmd = f"sapcontrol -nr {self.ino} -function StopSystem"
                os.WEXITSTATUS(os.system(f"sleep 5; {tout_cmd} {action_cmd}"))
                # DONE HDB stop is only valid for Scale-Up but does not need the instance number
            if (isLostIndexserver and self.action_on_lost == "firstStopThenKill"):
                # this is lab code only. Do not use it in customer or partner systems.
                # this code could be removed at any time without notice
                # the code does not promise that it will be part of any product later
                msg = f"LOST: firstStopThenKill instance. action_on_lost={self.action_on_lost}"
                self.logTimestamp(method, episode, msg)
                self.tracer.info(msg)
                action_cmd = (f"/usr/bin/SAPHanaSR-hookHelper --sid={mySID}"
                              f" --ino={self.ino} --case=firstStopThenKill")
                os.WEXITSTATUS(os.system(f"sleep 5; {action_cmd}"))
            if (isLostIndexserver and self.action_on_lost == "attr"):
                # this is lab code only. Do not use it in customer or partner systems.
                # this code could be removed at any time without notice
                # the code does not promise that it will be part of any product later
                msg = (f"LOST: set cluster attribute. action_on_lost={self.action_on_lost}"
                       " is currently not implemented")
                self.logTimestamp(method, episode, msg)
                self.tracer.info(msg)
                # TODO add attribute code here
            return 0

except NameError as e:
    print(f"Could not find base class ({e})")
