"""
# ServiceEvents
# Author:       Janine Fuchs
# License:      GNU General Public License (GPL)
# Copyright:    (c) 2023, Janine Fuchs <jfuchs@redhat.com>

Use SAP HANA service events to update pacemaker cluster node attributes and
enable cluster resource agents to use the provided service state changes for further processing.

To use this SAP HANA HA/DR hook provider, add the following to the instance global.ini,
adjust values as required:

    [ha_dr_provider_ServiceEvents]
    provider = ServiceEvents
    path = /usr/share/SAPHanaSR/srHook
    execution_order = 2

    [trace]
    ha_dr_serviceevents = info

Currently this hook creates and updates a pacemaker cluster node attribute for
SAP HANA "indexserver" service state changes.

It requires a sudo entry to be configured for the SAP HANA SID user,
which allows the execution of the following command pattern:

    /usr/sbin/crm_attribute -n hana_<sid>_indexserver -v <state info> -l reboot

"""

import os
from datetime import datetime

try:
    from hdb_ha_dr.client import HADRBase
    import ConfigMgrPy
except ImportError as e:
    print("Module not found: {}".format(e))

SRHookName = "ServiceEvents"
SRHookVersion = "0.2.0"


def traceLog(self, method, output):
    traceFilepath = os.path.join(os.environ['SAP_RETRIEVAL_PATH'], 'trace', 'nameserver_serviceevents.trc')

    try:
        with open(traceFilepath, "a") as logfile:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f ')
            logMessage = "{} {}:[{}]".format(timestamp, method, output)
            logfile.write(logMessage + "\n")
            logfile.flush()

    except (RuntimeError, TypeError, NameError, OSError) as err:
        self.tracer.info("{}.{}() traceLog error {}".format(self.__class__.__name__, method, err))
        print("Error in traceLog(): {0}".format(err))

try:
    class ServiceEvents(HADRBase):

        def __init__(self, *args, **kwargs):
            super(ServiceEvents, self).__init__(*args, **kwargs)
            method = "init"
            logmsg = "init called"
            traceLog(self, method, logmsg)

        def about(self):
            method = "about"
            self.tracer.info("{}.{}() version {}".format(self.__class__.__name__, method, SRHookVersion))
            return {"provider_company": "Red Hat",
                    "provider_name": "ServiceEvents",
                    "provider_description": "Update cluster node attributes based on HANA service state changes",
                    "provider_version": "1.0"}

        def srServiceStateChanged(self, parameters, **kwargs):
            method = "srServiceStateChanged"
            ## Debugging: log any event
            #logmsg = locals()
            #traceLog(self, method, logmsg))

            # Service parameters used for event processing
            service = parameters['service_name']
            status = parameters['service_status']
            previous_status = parameters['service_previous_status']
            timestamp = parameters['timestamp']

            # Filter conditions for disaster recognition
            is_indexserver = (service == "indexserver")
            service_start = (status in ["starting"])
            service_stop = (status in ["stopping"])
            service_ok = (status in ["yes"])
            service_down = (status in ["no"])

            indexserver_attribute = ""

            # Define cluster node attribute values on specific events
            if is_indexserver and service_stop:
                indexserver_attribute = "stopping"

            elif is_indexserver and service_start:
                indexserver_attribute = "starting"

            elif is_indexserver and service_ok:
                indexserver_attribute = "running"

            elif is_indexserver and service_down:
                indexserver_attribute = "down"

            # Run cluster node attribute update command and log event information
            if is_indexserver and indexserver_attribute != "":

                logmsg1 = "Service status changed for {}: previous status '{}' -> new status '{}' ({})".format(service, previous_status, status, timestamp)
                logmsg2 = "Detected service event ({}) => informing cluster".format(service)
                traceLog(self, method, logmsg1)
                traceLog(self, method, logmsg2)
                self.tracer.info(logmsg1)
                self.tracer.info(logmsg2)

                service_sid = ConfigMgrPy.sapgparam('SAPSYSTEMNAME')

                exec_command = "sudo /usr/sbin/crm_attribute -n hana_{}_indexserver -v {} -l reboot".format(service_sid.lower(), indexserver_attribute)

                cmdrc = os.WEXITSTATUS(os.system(exec_command))
                traceLog(self, method, exec_command)

            return 0

except NameError as e:
    print("Could not find base class ({0})".format(e))
