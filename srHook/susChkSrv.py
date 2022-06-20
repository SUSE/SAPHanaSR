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
SRHookVersion = "0.0.1"
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
            self.tracer.info("{0}.{1}() version {2}, time_out {3}".format(self.__class__.__name__, method, SRHookVersion, self.time_out))

        def about(self):
            method = "about"
            self.tracer.info("{0}.{1}() version {2}".format(self.__class__.__name__, method, SRHookVersion))
            return {"provider_company": "SUSE",
                    "provider_name": "susChkSrv",  # class name
                    "provider_description": "Process service status changed events",
                    "provider_version": "1.0"}

        def srServiceStateChanged(self, ParamDict, **kwargs):
            method="srServiceStateChanged"
            self.tracer.info("{0} version {1}. Method {2} method called.".format(SRHookName, SRHookVersion, method))
            self.tracer.info("{0} {1} method called with Dict={2}".format(SRHookName, method, ParamDict))
            return 0

except NameError as e:
    print("Could not find base class ({0})".format(e))
