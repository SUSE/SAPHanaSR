# pylint: disable=invalid-name
# remark: avoid pylint to react on module name does't conform to snake_case
"""
# SAPHana
# Author:       Fabian Herschel, 2015
# License:      GNU General Public License (GPL)
# Copyright:    (c) 2015-2016 SUSE Linux GmbH
# Copyright:    (c) 2017-2022 SUSE LLC
"""
# pylint: enable=invalid-name
# remark: switch-on now name checking
try:
    from hdb_ha_dr.client import HADRBase
except ImportError as e:
    print(f"Module HADRBase not found - running outside of SAP HANA? - {e}")
import os


# To use this HA/DR hook provide please add the following lines to your global.ini:
#    [ha_dr_provider_susHanaSR]
#    provider = susHanaSR
#    path = /usr/share/SAPHanaSR-angi
#    execution_order = 1
#
#    [trace]
#    ha_dr_saphanasr = info
#
FH_SR_HOOK_VERSION = "1.001.1"


try:
    # remark: case style is given by external configuration
    # pylint: disable-next=C0103
    class susHanaSR(HADRBase):
        """ class susHanaSR to handle HADR events for srConnectionChanged """

        def __init__(self, *args, **kwargs):
            """ constructor - delegate construction to base class """
            super().__init__(*args, **kwargs)
            method = "init"
            self.my_sid = os.environ.get('SAPSYSTEMNAME')
            self.tracer.info(f"{self.__class__.__name__}.{method}()"
                             f" version {FH_SR_HOOK_VERSION}")

        def about(self):
            """ tell about the HADR hook """
            return {"provider_company": "SUSE",
                    "provider_name": "susHanaSR",  # class name
                    "provider_description": "Inform Cluster about SR state",
                    "provider_version": "1.0"}

        # pylint: disable-next=unused-argument,invalid-name,too-many-locals
        def srConnectionChanged(self, ParamDict, **kwargs):
            """ process srConnectionChanged event """
            method = "srConnectionChanged"
            self.tracer.info(f"susHanaSR {FH_SR_HOOK_VERSION}"
                             f" {self.__class__.__name__}.srConnectionChanged"
                             f" method called with Dict={ParamDict}")
            my_system_status = ParamDict["system_status"]
            self.my_sid = os.environ.get('SAPSYSTEMNAME')
            mysid_lower = self.my_sid.lower()
            my_in_sync = ParamDict["is_in_sync"]
            my_reason = ParamDict["reason"]
            my_site = ParamDict["siteName"]
            self.tracer.info(f"susHanaSR {self.__class__.__name__}.srConnectionChanged"
                             f" system_status={my_system_status} SID={self.my_sid}"
                             f" in_sync={my_in_sync} reason={my_reason}")
            if my_system_status == 15:
                my_srs = "SOK"
            else:
                if my_in_sync:
                    # ignoring the SFAIL, because we are still in sync
                    self.tracer.info(f"susHanaSR {FH_SR_HOOK_VERSION}"
                                     f" {self.__class__.__name__}.srConnectionChanged ignoring bad"
                                     f" SR status because of is_in_sync=True (reason={my_reason})")
                    my_srs = ""
                else:
                    my_srs = "SFAIL"
            if my_srs == "":
                my_msg = "### Ignoring bad SR status because of is_in_sync=True ###"
                self.tracer.info(f"{self.__class__.__name__}.{method}() {my_msg}\n")
            elif my_site == "":
                my_msg = "### Ignoring bad SR status because of empty site name in call params ###"
                self.tracer.info(f"{self.__class__.__name__}.{method}() {my_msg}\n")
            else:
                my_cmd = ("sudo /usr/sbin/crm_attribute"
                          f" -n hana_{mysid_lower}_site_srHook_{my_site}"
                          f"  -v {my_srs} -t crm_config -s SAPHanaSR")
                ret_code = os.system(my_cmd)
                my_msg = f"CALLING CRM: <{my_cmd}> ret_code={ret_code}"
                self.tracer.info(f"{self.__class__.__name__}.{method}() {my_msg}\n")
                fallback_file_name = f"../.crm_attribute.{my_site}"
                fallback_stage_file_name = f"../.crm_attribute.stage.{my_site}"
                if ret_code == 0:
                    #
                    # cluster attribute set was successfull - delete pending fallback file, if existing
                    try:
                        os.remove(fallback_file_name)
                        self.tracer.info(f"new event - pending fallback file {fallback_file_name} deleted")
                    except FileNotFoundError:
                        pass
                else:
                    #
                    # FALLBACK
                    # sending attribute to the cluster failed - using fallback method and write
                    # status to a file - RA to pick-up the value during next SAPHanaController
                    # monitor operation
                    #
                    my_msg = "sending attribute to the cluster failed - using file as fallback"
                    self.tracer.info(f"{self.__class__.__name__}.{method}() {my_msg}\n")
                    #
                    # cwd of hana is /hana/shared/<SID>/HDB00/<hananode> we use a relative path
                    # to cwd this gives us a <sid>adm permitted directory
                    # however we go one level up (..) to have the file accessible for all
                    # SAP HANA swarm nodes
                    #
                    attribute_name = f"hana_{mysid_lower}_site_srHook_{my_site}"
                    try:
                        with open(fallback_stage_file_name, "w", encoding="UTF-8") as fallback_file_obj:
                            fallback_file_obj.write(f"{attribute_name} = {my_srs}")
                    except PermissionError:
                        my_msg = f"ERROR: Permission denied for file {fallback_stage_file_name}"
                        self.tracer.error(f"{self.__class__.__name__}.{method}() {my_msg}\n")
                    except FileNotFoundError:
                        my_msg = f"ERROR: File not found error occured during creating file {fallback_stage_file_name}"
                        self.tracer.error(f"{self.__class__.__name__}.{method}() {my_msg}\n")
                    except OSError as oerr:
                        my_msg = f"ERROR: OS error occured during creating file {fallback_stage_file_name}: {oerr}"
                        self.tracer.error(f"{self.__class__.__name__}.{method}() {my_msg}\n")
                    #
                    # release the stage file to the original name (move is used to be atomic)
                    #      .crm_attribute.stage.<site> is renamed to .crm_attribute.<site>
                    #
                    try:
                        os.rename(fallback_stage_file_name, fallback_file_name)
                    except PermissionError:
                        my_msg = f"ERROR: Permission denied to move file {fallback_stage_file_name} to {fallback_file_name}"
                        self.tracer.error(f"{self.__class__.__name__}.{method}() {my_msg}\n")
                    except FileNotFoundError:
                        my_msg = f"ERROR: File not found error occured during moving file {fallback_stage_file_name} to {fallback_file_name}"
                        self.tracer.error(f"{self.__class__.__name__}.{method}() {my_msg}\n")
                    except OSError as oerr:
                        my_msg = f"ERROR: OS error occured during moving file {fallback_stage_file_name} to {fallback_file_name}: {oerr}"
                        self.tracer.error(f"{self.__class__.__name__}.{method}() {my_msg}\n")
            return 0
except NameError as e:
    print(f"Could not find base class ({e})")
