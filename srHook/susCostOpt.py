# pylint: disable=invalid-name,fixme,broad-except
"""
# susCostOpt.py
# Authors:      Angela Briel, Fabian Herschel, June 2022
# License:      GNU General Public License (GPL)
# Copyright:    (c) 2022 SUSE LLC

susCostOpt
purpose: reconfigures the SAP HANA instance during the postTakeover event to allow the
new primary to consume the needed resources. Currently the hook reconfigures the
global allocation limit and the pre-load of column tables.

To use this HA/DR hook provide please add the following lines (or similar) to your global.ini:
    [ha_dr_provider_susCostOpt]
    provider = susCostOpt
    path = /usr/share/SAPHanaSR
    userKey = costoptkey
    execution_order = 1
    costopt_primary_global_allocation_limit = limit-in-mb # optional only for special use-cases
    costopt_primary_global_allocation_limit = 0  # optional, as of global.ini documentation
                                                   defines limitation by current resources

    [trace]
    ha_dr_suscostopt = info

The hook needs to be installed on the second node.
"""

# loading classes and libraries
import os

# pylint: enable=invalid-name
try:
    from hdbcli import dbapi
except ImportError as e:
    print(f"Module dbapi not found - install the missing SAP Python Driver 'hdbcli' - {e}")

try:
    from hdb_ha_dr.client import HADRBase
except ImportError as e:
    print(f"Module HADRBase not found - running outside of SAP HANA? - {e}")

# parameter section
FHSRHOOKVERSION = "1.001.1"
USERKEY_DFLT = "saphanasr_<sid>_costopt"
#


# pylint: disable-next=invalid-name
class susCostOpt(HADRBase):
    """ class for HADR hook script to handle postTakeover events """

    def __init__(self, *args, **kwargs):
        # delegate construction to base class
        super().__init__(*args, **kwargs)
        method = "init"
        my_sid_upper = os.environ.get('SAPSYSTEMNAME')
        mysid = my_sid_upper.lower()

        # read settings from global.ini
        # read userkey
        if self.config.hasKey("userkey"):
            self.userkey = self.config.get("userkey")
        else:
            self.userkey = USERKEY_DFLT.replace("<sid>", mysid)

        # read costopt_primary_global_allocation_limit
        primary_global_alloc_limit = 0
        if self.config.hasKey("costopt_primary_global_allocation_limit"):
            # parameter costopt_primary_global_allocation_limit is set
            # so adjust global_allocation_limit to the defined value
            primary_global_alloc_limit = self.config.get("costopt_primary_global_allocation_limit")
            self.sql_set_memory = ("ALTER SYSTEM ALTER CONFIGURATION ('global.ini','SYSTEM')"
                                   " SET ('memorymanager','global_allocation_limit') ="
                                   f"'{primary_global_alloc_limit}' WITH RECONFIGURE")
        else:
            # parameter costopt_primary_global_allocation_limit is NOT set
            # so just unset global_allocation_limit
            self.sql_set_memory = ("ALTER SYSTEM ALTER CONFIGURATION ('global.ini','SYSTEM')"
                                   " UNSET ('memorymanager','global_allocation_limit')"
                                   " WITH RECONFIGURE")
        # unset preload_column_tables
        self.sql_set_preload = ("ALTER SYSTEM ALTER CONFIGURATION ('global.ini','SYSTEM')"
                                " UNSET ('system_replication','preload_column_tables')"
                                " WITH RECONFIGURE")

        self.tracer.info(f"{self.__class__.__name__}.{method}() version {FHSRHOOKVERSION},"
                         f" userkey {self.userkey}, sid {mysid},"
                         f" primary_global_alloc_limit {primary_global_alloc_limit}")

    def about(self):
        """ tell something about the HADR hook script """
        method = "about"
        self.tracer.info(f"{self.__class__.__name__}.{method}() version {FHSRHOOKVERSION}")
        desc = ("postTakeover script to reset parameters to default or set parameters as"
                " defined in global.ini.")
        return {"provider_company": "SUSE",
                "provider_name": "susCostOpt",  # class name
                "provider_description": desc,
                "provider_version": "1.0"}

    # pylint: disable-next=unused-argument, invalid-name
    def postTakeover(self, rc, **kwargs):
        """Post takeover hook."""
        method = "postTakeover"
        self.tracer.info(f"{self.__class__.__name__}.{method}() method called with rc={rc}")
        # TODO PRIO4: How to handle return code (rc) not equal to 0 or 1?
        # And to we need to differ rc==0 and rc==1
        if rc in (0, 1):
            # takeover finished with returnocde 0 or 1
            # open database connection
            try:
                connection = dbapi.connect(
                    key=self.userkey,
                    # address='localhost',port=dbport,user=dbuser,passwort=dbpwd,
                )
            except Exception as exerr:
                self.tracer.info(f"error during database connection - {exerr}.")
                return 1

            # check, if database connection was successfull
            if not connection.isconnected():
                self.tracer.info("database connection could not be established")
                return 1

            cursor = connection.cursor()
            try:
                self.tracer.info(f"sqlstatement: {self.sql_set_memory}")
                cursor.execute(self.sql_set_memory)
            except Exception as exerr:
                self.tracer.info("error during execution of the sql statement"
                                 f" {self.sql_set_memory} - {exerr}.")
            try:
                self.tracer.info(f"sqlstatement: {self.sql_set_preload}")
                cursor.execute(self.sql_set_preload)
            except Exception as exerr:
                self.tracer.info("error during execution of the sql statement"
                                 f" {self.sql_set_preload} - {exerr}.")

            # commit the changes in the database
            connection.commit()
            # close cursor
            cursor.close()
            # close database connection, disconnect from server
            connection.close()

        self.tracer.info("leave postTakeover hook")
        return 0
