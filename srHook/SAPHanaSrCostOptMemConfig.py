"""
# Copyright:    (c) 2022 SUSE LLC

SAPHanaSrCostOptMemConfig
prepared SQL statements to remove memory allocation limit and the switch-off of the pre-load of column tables after takeover from primary to the secondary site in case of a cost optimized scenario

To use this HA/DR hook provide please add the following lines (or similar) to your global.ini:
    [ha_dr_provider_SAPHanaSrCostOptMemConfig]
    provider = SAPHanaSrCostOptMemConfig
    path = /usr/share/SAPHanaSR
    userKey = costoptkey
    execution_order = 1
    costopt_primary_global_allocation_limit = limit-in-mb # optional only for special use-cases

    [trace]
    ha_dr_saphanasrcostoptmemconfig = info

The hook needs to be installed on the second node.
"""

# loading classes and libraries
import os
try:
    from hdbcli import dbapi
except ImportError as e:
    print("Module dbapi not found - install the missing SAP Python Driver 'hdbcli' - {0}".format(e))

try:
    from hdb_ha_dr.client import HADRBase
except ImportError as e:
    print("Module HADRBase not found - running outside of SAP HANA? - {0}".format(e))

# parameter section
fhSRHookVersion = "0.160.1"
userkey_dflt = "saphanasr_<sid>_costopt"
#


class SAPHanaSrCostOptMemConfig(HADRBase):

    def __init__(self, *args, **kwargs):
        # delegate construction to base class
        super(SAPHanaSrCostOptMemConfig, self).__init__(*args, **kwargs)
        method = "init"
        mySID = os.environ.get('SAPSYSTEMNAME')
        mysid = mySID.lower()

        # read settings from global.ini
        # read userkey
        if self.config.hasKey("userkey"):
            self.userkey = self.config.get("userkey")
        else:
            self.userkey = userkey_dflt.replace("<sid>", mysid)

        # read costopt_primary_global_allocation_limit
        costopt_primary_global_allocation_limit = 0
        if self.config.hasKey("costopt_primary_global_allocation_limit"):
            # parameter costopt_primary_global_allocation_limit is set
            # so adjust global_allocation_limit to the defined value
            costopt_primary_global_allocation_limit = self.config.get("costopt_primary_global_allocation_limit")
            self.sql_set_memory = "ALTER SYSTEM ALTER CONFIGURATION ('global.ini','SYSTEM') SET ('memorymanager','global_allocation_limit') = '%s' WITH RECONFIGURE" % (costopt_primary_global_allocation_limit)
        else:
            # parameter costopt_primary_global_allocation_limit is NOT set
            # so just unset global_allocation_limit
            self.sql_set_memory = "ALTER SYSTEM ALTER CONFIGURATION ('global.ini','SYSTEM') UNSET ('memorymanager','global_allocation_limit') WITH RECONFIGURE"

        # unset preload_column_tables
        self.sql_set_preload = "ALTER SYSTEM ALTER CONFIGURATION ('global.ini','SYSTEM') UNSET ('system_replication','preload_column_tables') WITH RECONFIGURE"

        self.tracer.info("{0}.{1}() version {2}, userkey {3}, sid {4}, costopt_primary_global_allocation_limit {5}".format(self.__class__.__name__, method, fhSRHookVersion, self.userkey, mysid, costopt_primary_global_allocation_limit))

    def about(self):
        method = "about"
        self.tracer.info("{0}.{1}() version {2}".format(self.__class__.__name__, method, fhSRHookVersion))
        return {"provider_company": "SUSE",
                "provider_name": "SAPHanaSrCostOptMemConfig",  # class name
                "provider_description": "postTakeover script to reset parameters to default or set parameters as defined in global.ini.",
                "provider_version": "1.0"}


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
        method = "postTakeover"
        """Post takeover hook."""
        self.tracer.info("{0}.{1}() method called with rc={2}".format(self.__class__.__name__, method, rc))
        # TODO PRIO4: How to handle return code (rc) not equal to 0 or 1? And to we need to differ rc==0 and rc==1
        if rc == 0 or rc == 1:
            # takeover finished with returnocde 0 or 1
            connection = dbapi.connect(
                key=self.userkey,
                # address='localhost',port=dbport,user=dbuser,passwort=dbpwd,
            )
            cursor = connection.cursor()
            self.tracer.info("sqlstatement: {0}".format(self.sql_set_memory))
            cursor.execute(self.sql_set_memory)
            self.tracer.info("sqlstatement: {0}".format(self.sql_set_preload))
            cursor.execute(self.sql_set_preload)
            cursor.close()
        self.tracer.info("leave postTakeover hook")
        return 0
