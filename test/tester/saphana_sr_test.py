#!/usr/bin/python3
# pylint: disable=consider-using-f-string
# pylint: disable=fixme
# pylint: disable=line-too-long
# pylint: disable=broad-exception-caught
# pylint: disable=too-many-lines,too-many-statements,too-many-instance-attributes,too-many-public-methods,too-many-branches,too-many-locals,too-many-nested-blocks,
# pylint: disable=invalid-name
# TODO: legacy (classic) has "Sites" instead of "Site" (angi) and "Hosts" (classic/legacy) instead of "Host" (angi) --> could we set that via json files?
"""
 saphanasrtest.py
 Author:       Fabian Herschel, Mar 2023
 License:      GNU General Public License (GPL)
 Copyright:    (c) 2023-2026 SUSE LLC
"""

import time
import subprocess
import re
import sys
import json
import argparse
import random

# Version: 1.5.20250306
# for ssh remote calls this module uses paramiko
#from paramiko import SSHClient
import paramiko
# from paramiko import AutoAddPolicy

class SaphanasrTest:
    """
    class to check SAP HANA cluster during tests
    """
    version = "2.6.20260605"

    def message(self, msg, **kwargs):
        """
        message with formatted timestamp
        """
        stdout = kwargs.get('stdout', True)
        pre_cr = kwargs.get('pre_cr', False)
        # TODO: specify, if message should be written to stdout, stderr and/or log file
        date_time = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.run['r_id']:
            r_id = " [{}]".format(self.run['r_id'])
        else:
            r_id = ""
        msg_arr = msg.split(" ")
        if stdout:
            if pre_cr:
                print()
            message_type = msg_arr[0]
            core_message = " ".join(msg_arr[1:])
            print("{}{} {:<9s} {}".format(date_time, r_id, message_type, core_message), flush=True)
        try:
            if self.run['log_file_handle']:
                _l_msg = f"{date_time}{r_id} {msg_arr[0]:9}"
                _l_msg += ' '.join(msg_arr[1:])
                self.run['log_file_handle'].write(_l_msg + "\n")
                self.run['log_file_handle'].flush()
        except OSError:
            core_message = "Could not write log log file"
            print("{0} {1:<9s} {2}".format(date_time, "ERROR:", core_message), flush=True)

    def debug(self, msg, **kwargs):
        """
        debug output/log only if option debug is set
        """
        if self.config['debug']:
            self.message(msg, **kwargs)

    def __init__(self, *args, **kwargs):
        """
        constructor
        """
        random.seed()
        self.run = { 'log_file_handle': None, 'r_id': None, 'test_rc': 0, 'count': 1 }
        self.run['r_id'] = random.randrange(10000,99999,1)
        cmdparse = kwargs.get('cmdparse', True)
        self.config = { 'test_file': "-",
                        'defaults_file': None,
                        'properties_file': "properties.json",
                        'log_file': "",
                        'jsonOut': None,
                        'repeat': 1,
                        'dump_failures': False,
                        'remote_node': None,
                        'remote_nodes': [],
                        'printTestProperties': False,
                        'debug': False,
                        'user': 'root',
                        'password': None,
                        'on_fail_reaction': 'continue',
                        'check_host': True,
                        'use_sudo': False,
                      }
        self.result = { 'test_id': self.run['r_id'], 'config': self.config, 'test_name': '', 'topology': {}, 'steps': {} }
        self.dict_sr = {}
        self.test_data = {}
        # self.topolo = { 'pSite': None, 'sSite': None, 'pHost': None, 'sHost': None }
        self.topolo = {}
        self.topo_translate =  { 'global': 'Global', 'pSite': 'Site', 'sSite': 'Site', 'tSite': 'Site', 'fSite': 'Site', 'pHost': 'Host', 'sHost': 'Host', 'tHost': 'Host', 'fHost': 'Host' }
        self.debug("INIT: tester version: {}".format(self.version))
        self.__failed_role_counter__ = 0
        self.__min_failed_role_counter__ = 0
        self.__max_failed_role_counter__ = 0
        self.step_loops = [ "x" ]
        if cmdparse:
            self.debug("DEBUG: lib parses cmdline")
            parser = argparse.ArgumentParser()
            parser.add_argument("--testFile", help="specify the test file")
            parser.add_argument("--defaultsFile", help="specify the defaults file")
            parser.add_argument("--properties", help="specify the properties file")
            parser.add_argument("--remoteNode", help="cluster node to use for ssh connection")
            parser.add_argument("--simulate", help="only simulate, dont call actions",
                                action="store_true")
            parser.add_argument("--repeat", help="how often to repeat the test")
            parser.add_argument("--dumpFailures", help="print failed checks per loop",
                                action="store_true")
            parser.add_argument("--logFile", help="log file to write the messages")
            args = parser.parse_args()
            if args.testFile:
                self.message("PARAM: testFile: {}".format(args.testFile))
                self.config['test_file'] = args.testFile
            if args.defaultsFile:
                self.message("PARAM: defaultsFile: {}".format(args.defaultsFile))
                self.config['defaults_file'] = args.defaultsFile
            if args.properties:
                self.message("PARAM: properties: {}".format(args.properties))
                self.config['properties_file'] = args.properties
            if args.remoteNode:
                self.message("PARAM: remoteNode: {}".format(args.remoteNode))
                self.config['remote_node'] = args.remoteNode
            if args.repeat:
                self.message("PARAM: repeat: {}".format(args.repeat))
                self.config['repeat'] = int(args.repeat)
            if args.dumpFailures:
                self.message("PARAM: dumpFailures")
                self.config['dump_failures'] = args.dumpFailures
            if args.logFile:
                self.message("PARAM: logFile: {}".format(args.logFile))
                self.config['log_file'] = args.logFile
                # disable 'consider to use with ...' - I am pretty sure with does not match here
                # pylint: disable-next=R1732
                self.run['log_file_handle'] = open(self.config['log_file'], 'a', encoding="utf-8")
        else:
            self.debug("DEBUG: lib skips parsing cmdline")
        # TODO: move action and action_type dictionary to a config file
        self.action_types = {
                        'kill_inst': { 'cmd': "su - @@sid@@adm HDB kill-9", 'sudo': "sudo -u @@sid@@adm --login /usr/sap/@@SID@@/HDB@@INO@@/HDB kill-9" },
                        'kill_sap_service': { 'cmd': "pkill -u @@sid@@adm --signal 11 @@param1@@", 'sudo': "sudo -u root pkill -u @@sid@@adm --signal 11 @@param1@@" },
                        'kill_node': { 'cmd': "/usr/bin/systemctl reboot --force", 'sudo': "sudo -u root @@cmd@@"},
                        'cluster_node': { 'cmd': "/usr/sbin/crm node @@param1@@ @@node@@", 'sudo': "sudo -u root @@cmd@@"},
                        'cluster_resource': { 'cmd': "/usr/sbin/crm resource @@param1@@ @@param2@@", 'sudo': "sudo -u root @@cmd@@" },
                        'hana_takeover': { 'cmd': "su - @@sis@@adm -c 'hdbnsutil -sr_takeover'", 'sudo': "sudo -u @@sid@@adm --login /usr/sap/@@SID@@/HDB@@INO@@/exe/hdbnsutil -sr_takeover" },
                        'block_ip': { 'cmd': "/usr/bin/iptables -I INPUT -s @@pHost@@ -j DROP", 'sudo': "sudo -u root @@cmd@@" },
                        'sleep': { 'cmd': "sleep @@actParam1@@" },
                        'shell': { 'cmd': "@@actParamAll@@" }
                       }
        self.actions = {
                        #
                        # hana HAregion
                        #
                        'kill_prim_inst': { 'type': 'hana', 'ha_dr': 'HA', 'node': 'pHost', 'action_type': 'kill_inst' }, 
                        'kill_prim_worker_inst': { 'type': 'hana', 'ha_dr': 'HA', 'node': 'pHost', 'action_type': 'kill_inst'},
                        'kill_secn_inst': { 'type': 'hana', 'ha_dr': 'HA', 'node': 'sHost', 'action_type': 'kill_inst'},
                        'kill_secn_worker_inst': { 'type': 'hana', 'ha_dr': 'HA', 'node': 'sHost', 'action_type': 'kill_inst'},
                        'kill_prim_indexserver': { 'type': 'hana', 'ha_dr': 'HA', 'node': 'pHost', 'action_type': 'kill_sap_service', 'param1': 'hdbindexserver'},
                        'kill_secn_indexserver': { 'type': 'hana', 'ha_dr': 'HA', 'node': 'sHost', 'action_type': 'kill_sap_service', 'param1': 'hdbindexserver'},
                        'kill_prim_worker_indexserver': { 'type': 'hana', 'ha_dr': 'HA', 'node': 'pWorker', 'action_type': 'kill_sap_service', 'param1': 'hdbindexserver'},
                        'kill_secn_worker_indexserver': { 'type': 'hana', 'ha_dr': 'HA', 'node': 'sWorker', 'action_type': 'kill_sap_service', 'param1': 'hdbindexserver'},
                        'kill_prim_nameserver': { 'type': 'hana', 'ha_dr': 'HA', 'node': 'pWorker', 'action_type': 'kill_sap_service', 'param1': 'hdbnameserver'},
                        'kill_secn_nameserver': { 'type': 'hana', 'ha_dr': 'HA', 'node': 'sWorker', 'action_type': 'kill_sap_service', 'param1': 'hdbnameserver'},
                        'kill_prim_xsengine': { 'type': 'hana', 'ha_dr': 'HA', 'node': 'pHost', 'action_type': 'kill_sap_service', 'param1': ' hdbxsengine'},
                        'kill_secn_xsengine': { 'type': 'hana', 'ha_dr': 'HA', 'node': 'sHost', 'action_type': 'kill_sap_service', 'param1': ' hdbxsengine'},
                        'bmt': { 'type': 'hana', 'ha_dr': 'HA', 'node': 'sHost', 'action_type': 'hana_takeover'},
                        #
                        # hana DRregion
                        #
                        'kill_third_inst': { 'type': 'hana', 'ha_dr': 'DR', 'node': 'tHost', 'action_type': 'kill_inst'},
                        'kill_third_worker_inst': { 'type': 'hana', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False, 'action_type': 'kill_inst'},
                        'kill_fourth_inst': { 'type': 'hana', 'ha_dr': 'DR', 'node': 'fHost', 'action_type': 'kill_inst'},
                        'kill_fourth_worker_inst': { 'type': 'hana', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False , 'action_type': 'kill_inst'},
                        'kill_third_indexserver': { 'type': 'hana', 'ha_dr': 'DR', 'node': 'tHost', 'action_type': 'kill_sap_service', 'param1': 'hdbindexserver'},
                        'kill_fourth_indexserver': { 'type': 'hana', 'ha_dr': 'DR', 'node': 'fHost', 'action_type': 'kill_sap_service', 'param1': 'hdbindexserver'},
                        'kill_third_worker_indexserver': { 'type': 'hana', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False, 'action_type': 'kill_sap_service', 'param1': 'hdbindexserver' },
                        'kill_fourth_worker_indexserver': { 'type': 'hana', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False, 'action_type': 'kill_sap_service', 'param1': 'hdbindexserver' },
                        'kill_third_nameserver': { 'type': 'hana', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False, 'action_type': 'kill_sap_service', 'param1': 'hdbnameserver' },
                        'kill_fourth_nameserver': { 'type': 'hana', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False, 'action_type': 'kill_sap_service', 'param1': 'hdbnameserver' },
                        'kill_third_xsengine': { 'type': 'hana', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False, 'action_type': 'kill_sap_service', 'param1': 'hdbxsengine' },
                        'kill_fourth_xsengine': { 'type': 'hana', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False, 'action_type': 'kill_sap_service', 'param1': 'hdbxsengine' },
                        #
                        # cluster HAregion
                        #
                        'ssn': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'sHost', 'action_type': 'cluster_node', 'param1': 'standby'},
                        'osn': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'sHost', 'action_type': 'cluster_node', 'param1': 'online'},
                        'spn': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'pHost', 'action_type': 'cluster_node', 'param1': 'standby'},
                        'opn': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'pHost', 'action_type': 'cluster_node', 'param1': 'online'},
                        'cleanup': { 'type': 'cluster', 'ha_dr': 'HA', 'connection': 'remote', 'action_type': 'cluster_resource', 'param1': 'cleanup', 'param2': '@@mst_resource@@'},
                        'kill_secn_node': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'sHost', 'action_type': 'kill_node'},
                        'kill_secn_worker_node': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'sWorker', 'action_type': 'kill_node'},
                        'kill_secn_worker2_node': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'sWorker2', 'action_type': 'kill_node'},
                        'kill_prim_node': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'pHost', 'action_type': 'kill_node'},
                        'kill_prim_worker_node': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'pWorker', 'action_type': 'kill_node'},
                        'stop_hana_resource': { 'type': 'cluster', 'ha_dr': 'HA', 'connection': 'remote', 'action_type': 'cluster_resource', 'param1': 'stop', 'param2': '@@mst_resource@@'},
                        'start_hana_resource': { 'type': 'cluster', 'ha_dr': 'HA', 'connection': 'remote', 'action_type': 'cluster_resource', 'param1': 'start', 'param2': '@@mst_resource@@'},
                        'simulate_split_brain': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'sHost', 'action_type': 'block_ip'},
                        'standby_prim_worker_node': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'pWorker', 'action_type': 'cluster_node', 'param1': 'standby'},
                        'online_prim_worker_node': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'pWorker', 'action_type': 'cluster_node', 'param1': 'online'},
                        'standby_secn_worker_node': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'sWorker', 'action_type': 'cluster_node', 'param1': 'standby'},
                        'online_secn_worker_node': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'sWorker', 'action_type': 'cluster_node', 'param1': 'online'},
                        'ban_prim_hana_resource': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'pHost', 'action_type': 'cluster_resource', 'param1': 'ban'},
                        'ban_secn_hana_resource': { 'type': 'cluster', 'ha_dr': 'HA', 'node': 'sHost', 'action_type': 'cluster_resource', 'param1': 'ban'},
                        #
                        # cluster DRregion
                        #
                        'standby_fourth_node': { 'type': 'cluster', 'ha_dr': 'DR', 'node': 'fHost', 'action_type': 'cluster_node', 'param1': 'standby'},
                        'online_fourth_node':  { 'type': 'cluster', 'ha_dr': 'DR', 'node': 'fHost', 'action_type': 'cluster_node', 'param1': 'online'},
                        'standby_third_node':  { 'type': 'cluster', 'ha_dr': 'DR', 'node': 'tHost', 'action_type': 'cluster_node', 'param1': 'standby'},
                        'online_third_node':   { 'type': 'cluster', 'ha_dr': 'DR', 'node': 'tHost', 'action_type': 'cluster_node', 'param1': 'online'},
                        'kill_fourth_node':    { 'type': 'cluster', 'ha_dr': 'DR', 'node': 'fHost', 'action_type': 'kill_node'},
                        'kill_fourth_worker_node':{ 'type': 'cluster', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False, 'action_type': 'kill_node' },
                        'kill_third_node':     { 'type': 'cluster', 'ha_dr': 'DR', 'node': 'tHost', 'action_type': 'kill_node'},
                        'kill_third_worker_node':    { 'type': 'cluster', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False, 'action_type': 'kill_node'},
                        'simulate_split_brain_dr':   { 'type': 'cluster', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False, 'action_type': 'kill_node'},
                        'standby_third_worker_node': { 'type': 'cluster', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False, 'action_type': 'kill_node'},
                        'online_third_worker_node':  { 'type': 'cluster', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False, 'action_type': 'kill_node'},
                        'standby_fourth_worker_node': { 'type': 'cluster', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False, 'action_type': 'kill_node'},
                        'online_fourth_worker_node':  { 'type': 'cluster', 'ha_dr': 'DR', 'node': 'xx', 'implemented': False, 'action_type': 'kill_node' },
                        #
                        # os
                        #
                        'shell': { 'type': 'os', 'connection': 'local', 'action_type': 'shell' },
                        'sleep': { 'type': 'os', 'connection': 'local', 'action_type': 'sleep' }
                       }

    def __resolve__(self, line, **kargs):
        # TODO: resolver-variables: @@actParam1@@ @@actParamAll@@ @@cmd@@ @@INO@@ @@mst_resource@@ @@node@@ @@param1@@ @@param2@@ @@pHost@@ (@@service@@) @@sid@@ @@SID@@
        """
        __resolver__ replaces all occurences of patterns @@xx@@ in line
        l_resolver called by: create_pxe_file, create_config_files

        params:
            line - source text line to be translated
        Object attributes:
            self.l_replace - dictionary of replacement rules
        """
        replace = kargs.get('replace', None)

        still_resolve = True

        repl_line = line
        while still_resolve:
            still_resolve = False
            for r_key in replace:
                orig_line = repl_line
                repl_val = replace.get(r_key,"")
                repl_line = orig_line.replace(r_key, replace.get(r_key))
                if orig_line != repl_line:
                    still_resolve = True
        return repl_line


    def __insert_to_area__(self, area, the_object):
        """ insert an object dictionary to an area dictionary """
        l_sr = self.dict_sr.copy()
        if area in l_sr:
            l_dic = l_sr[area].copy()
            l_dic.update(the_object)
            l_sr[area].update(l_dic)
        else:
            l_dic = { area: the_object }
            l_sr.update(l_dic)
        self.dict_sr = l_sr.copy()

    def __get_object__(self, area, object_name):
        """ get an object dictionary inside the area dictionary """
        l_sr = self.dict_sr.copy()
        if area in l_sr:
            if object_name in l_sr[area]:
                return l_sr[area][object_name]
        return None

    def create_object(self, object_name, key, val):
        """ create a key: value dictionary for object object_name """
        l_obj = { object_name: { key: val } }
        return l_obj

    def __insert_to_object__(self, the_object, key, value):
        """ insert a key-value pair into the object dictionary """
        l_obj = the_object
        l_dic = { key: value }
        l_obj.update(l_dic)
        return l_obj

    def read_saphana_sr(self, **kargs):
        """
        method to read SAPHanaSR-showAttr cluster attributes and create a nested dictionary
        structure representing the data
        """
        connect_host = kargs.get('connect_hosts', None)
        read_json = self.config.get('jsonInSimulate', None)
        #cmd = [ './helpSAPHanaSR-showAttr', '--format=script'  ]
        cmd = "/usr/bin/SAPHanaSR-showAttr --format=tester --select=all"
        if read_json:
            cmd = f"{cmd} --read_json {read_json}"
        if self.config['use_sudo']:
            cmd = f"sudo -u root {cmd}"
        self.debug(f'TOPO: cmd = {cmd}')
        self.dict_sr={}
        sr_out = ""
        #self.message("remote node broken !!")
        # try other remoteNodes (if given via parameter)
        #self.message(f"len array {len(self.config['remote_nodes'])}")
        l_remotes = []
        s_remote_node = self.config.get('remote_node', None)
        if s_remote_node:
            l_remotes.append(s_remote_node)   # stored remote last succesful remote node on first place
        if connect_host:
            l_remotes.append(connect_host)
        if len(self.config['remote_nodes']) > 1:
            l_remotes.extend(self.config['remote_nodes'])
        #
        # make list unique:
        #
        l_remotes = list(dict.fromkeys(l_remotes))
        switched_remote = False
        for remote_node in l_remotes:
            # self.message(f"test now with host {remote_node}")
            if remote_node == "localhost":
                # TODO PRIO3: capture_output is only available since python 3.8.20
                local_sr = subprocess.run(cmd.split(), capture_output=True, check=False)
                if local_sr.returncode != 20000:
                    if switched_remote:
                        self.message("STATUS: get data from localhost")
                        self.config['remote_node'] = remote_node
                        switched_remote = False
                    sr_out = local_sr.stdout.decode()
                    break
            else:
                result_sr = self.__do_ssh__(remote_node, self.config['user'], cmd, timeout=15, password=self.config['password'])
                if result_sr[2] != 20000:
                    if switched_remote:
                        self.message(f"STATUS: get data from {remote_node}")
                        self.config['remote_node'] = remote_node
                        switched_remote = False
                    sr_out = result_sr[0]
                    break
            self.message(f"STATUS: FAILED to get data from {remote_node}")
            switched_remote = True
        for line in sr_out.splitlines():
            # match and split: <area>/<object>/<key-value>
            match_obj = re.search("(.*)/(.*)/(.*)", line)
            if match_obj:
                area = match_obj.group(1)
                object_name = match_obj.group(2)
                key_val = match_obj.group(3)
                # match and split <key>="<value>"
                match_obj = re.search("(.*)=\"(.*)\"", key_val)
                key = match_obj.group(1)
                val = match_obj.group(2)
                l_obj=self.__get_object__(area, object_name)
                if l_obj:
                    self.__insert_to_object__(l_obj,key,val)
                else:
                    l_obj = self.create_object(object_name, key, val)
                    self.__insert_to_area__(area, l_obj)
        return 0

    def get_area_object_by_key_val(self, area_name, search_criteria, **kwargs):
        """ method to search in SR for an ObjectName filtered by 'area' and key=value """
        # sloppy might be need to set per search-criteria (e.g. True for roles not False for site)
        # Query runs from area-level via object-level. Then search for key=value.
        l_sloppy = kwargs.get('sloppy', False)
        l_multi = kwargs.get('multi', False)
        self.debug(f"DEBUG: DBG1 l_sloppy == {l_sloppy}, l_multi == {l_multi}")
        object_name = None
        object_names = []
        l_sr = self.dict_sr
        # check, if 'area' is in the sr-data-dictionary
        if area_name in l_sr:
            l_area = l_sr[area_name]
            # loop over all objets in area to check against criteria
            for k in l_area.keys():
                l_obj = l_area[k]
                # loop over multiple search-criteria (key/value)
                all_match = True
                for search_key in search_criteria.keys():
                    search_value = search_criteria[search_key]
                    if search_key in l_obj:
                        if l_sloppy:
                            # search value by regexp
                            if not re.search(search_value, l_obj[search_key]):
                                all_match = False
                        else:
                            if not l_obj[search_key] == search_value:
                                all_match = False
                    else:
                        all_match = False
                if all_match:
                    object_names.append(k)
                    object_name = k
                    if not l_multi:
                        break
        if l_multi:
            return object_names
        return object_name

    def get_value(self, area_name, object_name, key):
        """
        method to query the value of a key (e.g. 'msn') for an object
        (e.g. site 'MAINZ' inside an area (e.g. 'Site')
        """
        # Query runs from area-level via object-level to key-level
        l_value = None
        l_sr = self.dict_sr
        if area_name in l_sr:
            l_area = l_sr[area_name]
            if object_name in l_area:
                l_obj = l_area[object_name]
                if key in l_obj:
                    l_value = l_obj[key]
                else:
                    self.debug(f'DEBUG: key {key} not found')
        return l_value

    def pretty_print(self, dictionary,level):
        """ debug method for nested dictionary """
        print("{")
        count = 0
        for k in dictionary.keys():
            if count > 0:
                print(",")
            if isinstance(dictionary[k],dict):
                print("'{}': ".format(k))
                self.pretty_print(dictionary[k], level+1)
            else:
                print("'{}': '{}'".format(k,dictionary[k]))
            count = count + 1
        print("}")

    def read_test_file(self):
        """ read Test Description, optionally defaultchecks and properties """
        if self.config['defaults_file']:
            #print(f"read defaults file {self.config['defaults_file']}")
            with open(self.config['defaults_file'], encoding="utf-8") as dc_fh:
                self.test_data.update(json.load(dc_fh))
        if self.config['test_file'] == "-":
            self.test_data.update(json.load(sys.stdin))
        else:
            try:
                with open(self.config['test_file'], encoding="utf-8") as tf_fh:
                    #print(f"read test file {self.config['test_file']}")
                    self.test_data.update(json.load(tf_fh))
            except FileNotFoundError as e_file:
                self.message(f"ERROR: File error: {e_file}")
                return 1
            # pylint: disable=broad-exception-caught
            except (PermissionError, Exception) as e_generic:
                self.message(f"ERROR: File error: {e_generic}")
                return 1
        if self.config['properties_file']:
            #print(f"read properties file {self.config['properties_file']}")
            try:
                with open(self.config['properties_file'], encoding="utf-8") as prop_fh:
                    self.test_data.update(json.load(prop_fh))
            except FileNotFoundError as e_file:
                self.message(f"ERROR: File error: {e_file}")
                return 1
            # pylint: disable=broad-exception-caught
            except (PermissionError, Exception) as e_generic:
                self.message(f"ERROR: File error: {e_generic}")
                return 1
        self.run['test_id'] = self.test_data['test']
        self.result.update({'test_name': self.run['test_id']})
        self.debug("DEBUG: test_data: {}".format(str(self.test_data)),
                        stdout=False)
        return 0

    def write_test_properties(self, topology):
        """
        write_test_properties - write bash test properties file so bash test helper could source the key-value settings
        """
        with open(".test_properties", 'w', encoding="utf-8") as test_prop_fh:
            ha_or_dr = topology.get('ha_or_dr','HA')
            if ha_or_dr == "HA":
                test_prop_fh.write(f"node01=\"{topology.get('pHost','node01')}\"\n")
                test_prop_fh.write(f"node02=\"{topology.get('sHost','node02')}\"\n")
                test_prop_fh.write(f"pHost=\"{topology.get('pHost','node01')}\"\n")
                test_prop_fh.write(f"sHost=\"{topology.get('sHost','node02')}\"\n")
                pWorker = topology.get('pWorker',None)
                if pWorker:
                    test_prop_fh.write(f"pWorker=\"{pWorker}\"\n")
                sWorker = topology.get('sWorker',None)
                if sWorker:
                    test_prop_fh.write(f"sWorker=\"{sWorker}\"\n")
            elif ha_or_dr == "DR":
                test_prop_fh.write(f"node01=\"{topology.get('tHost','node01')}\"\n")
                test_prop_fh.write(f"node02=\"{topology.get('fHost','node02')}\"\n")
                test_prop_fh.write(f"tHost=\"{topology.get('tHost','node01')}\"\n")
                test_prop_fh.write(f"fHost=\"{topology.get('fHost','node02')}\"\n")
            test_prop_fh.write(f"mstResource=\"{self.test_data.get('mstResource','')}\"\n")
            test_prop_fh.write(f"clnResource=\"{self.test_data.get('clnResource','')}\"\n")
            test_prop_fh.write(f"rscIPResource=\"{self.test_data.get('rscIPResource','')}\"\n")
            test_prop_fh.write(f"srMode=\"{self.test_data.get('srMode','sync')}\"\n")
            test_prop_fh.write(f"opMode=\"{self.test_data.get('opMode','logreplay')}\"\n")
            test_prop_fh.write(f"SID=\"{self.test_data.get('sid','C11')}\"\n")
            test_prop_fh.write(f"instNr=\"{self.test_data.get('instNo','00')}\"\n")
            test_prop_fh.write(f"sidadm=\"{self.test_data.get('sid','C11').lower()}adm\"\n")
            test_prop_fh.write(f"userkey=\"{self.test_data.get('userKey','')}\"\n")
            test_prop_fh.write(f"proxyUser=\"{self.config.get('user','')}\"\n")
            test_prop_fh.write(f"all_nodes=\"{self.config.get('all_nodes','')}\"\n")
            test_prop_fh.flush()

    def __add_failed__(self, area_object, key_val_reg, **kwargs):
        """ __add_failed__ ocument failed checks
        params: area_object, key_val_reg
        kwargs: list_of_failures
        """
        list_of_failures = kwargs.get('list_of_failures', None)
        fatal_check = False
        fatal_name = ""
        fatal_check = kwargs.get("fatal_check", False)
        fatal_name = kwargs.get("fatal_name", "")
        # step_id = kwargs.get("step_id", "")
        ( _area, _obj ) = area_object
        if 'failed' in self.run:
            _l_failed = self.run['failed']
            if fatal_check:
                _l_header = f"{_area}={_obj}: "
            else:
                _l_header = ""
        else:
            _l_failed = ""
            _l_header = f"{fatal_name}{_area}={_obj}: "
        ( _key, _val, _reg, _comp ) = key_val_reg
        #
        # also fill the failures list, if given
        #
        if isinstance(list_of_failures, list):
            #print(f"DBG: __add_failed__ list_of_failures.append()")
            list_of_failures.append({'area': _area, 'object_name': _obj, 'expect': {'var': _key, 'expr': _reg, 'comp': _comp }, 'have': {'var': _key, 'val': _val} })
        _l_failed += f'{_l_header} expect "{_key} {_comp} {_reg}", have "{_val}"; '
        self.run['failed'] = _l_failed
        self.debug("DEBUG: add-failed: " + self.__get_failed__(), stdout=False)
        #print(f"DBG: __add_failed__ list_of_failures={list_of_failures}")

    def __reset_failed__(self):
        """ deletes failed from the run dictionary """
        # wert für failed aus array entfernen
        if 'failed' in self.run:
            del self.run['failed']

    def __get_failed__(self):
        if 'failed' in self.run:
            return self.run['failed']
        return None

    def __run_check__(self, single_check, area_name, object_name, step_step, **kwargs):
        # match <key> <comp> <regExp>
        # TODO: maybe allow flexible whitespace <key><ws><comp><ws><value>
        match_obj = re.search("(.*) (==|!=|>|>=|<|<=|~|!~|>~|is|is not) (.*)", single_check)
        check_result = -1
        c_key = "x"
        c_comp = "x"
        c_reg_exp = "x"
        list_of_failures = kwargs.get('list_of_failures', None)
        if match_obj is None:
            self.message(f"ERROR: step={step_step} unknown comperator in {single_check}")
            check_result = 2
        try:
            c_key = match_obj.group(1)
            c_comp = match_obj.group(2)
            c_reg_exp = match_obj.group(3)
        except Exception:
            self.message(f"ERROR: step={step_step} {single_check} does not match <key> <comp> <value>")   # TODO PRIO3: change from technical to user-friendly message
        l_sr = self.dict_sr
        # fail_msg = "MISSED"
        fatal_check = kwargs.get('fatal_check', False)
        fatal_name = kwargs.get('fatal_name', "")
        #
        # rewrite key, if it contains a string @@sid@@ this is needed e.g. to match lpa_<sid>_lpt
        #
        #print(f"c_key={c_key}")
        match_obj_key = re.search("(.*)@@sid@@(.*)", c_key)
        try:
            if match_obj_key is not None:
                #print(f"match c_key={c_key} group1={match_obj_key.group(1)} group2={match_obj_key.group(2)}")
                c_key = match_obj_key.group(1) + self.test_data['sid'].lower() + match_obj_key.group(2)
                #print(f"rewrite c_key={c_key}")
        except Exception:
            self.message(f"ERROR: step={step_step} c_comp and/or c_reg_exp not found in {single_check}")   # TODO PRIO3: change from technical to user-friendly message

        c_reg_exp_a = ""
        c_reg_exp_b = ""
        try:
            if c_comp == ">~":
                comp_obj = re.search("(.*):(.*)",c_reg_exp)
                c_reg_exp_a = comp_obj.group(1)
                c_reg_exp_b = comp_obj.group(2)
        except (IndexError, AttributeError):
            pass
        self.debug(f"DEBUG: ckey:{c_key} c_comp:{c_comp} c_reg_exp:{c_reg_exp} c_reg_exp_a:{c_reg_exp_a} c_reg_exp_b:{c_reg_exp_b}")
        found = False   # found is True, if the attribute has been FOUND (for all 'normal' compares) or is MISSING for compare "is None"
        if area_name in l_sr:
            l_area = l_sr[area_name]
            c_err = 1
            if object_name in l_area:
                l_obj = l_area[object_name]
                if c_key in l_obj:
                    l_val = l_obj[c_key]
                    found = True  # atttribute has been found for a compare (attribute is available)
                    # DONE '==' must be exact match, '~' is for regexp
                    if c_comp == "==":
                        if l_val == c_reg_exp:
                            c_err = 0
                    elif c_comp == "!=":
                        if l_val != c_reg_exp:
                            c_err = 0
                    elif c_comp == "~":
                        if re.search(c_reg_exp, l_val):
                            c_err = 0
                    elif c_comp == "!~":
                        if not re.search(c_reg_exp, l_val):
                            c_err = 0
                    elif c_comp == ">":
                        # TODO check l_val and c_reg_exp if they could transformed into int
                        if int(l_val) > int(c_reg_exp):
                            c_err = 0
                    elif c_comp == ">=":
                        # TODO check l_val and c_reg_exp if they could transformed into int
                        if int(l_val) >= int(c_reg_exp):
                            c_err = 0
                    elif c_comp == "<":
                        # TODO check l_val and c_reg_exp if they could transformed into int
                        if int(l_val) < int(c_reg_exp):
                            c_err = 0
                    elif c_comp == "<=":
                        # TODO check l_val and c_reg_exp if they could transformed into int
                        if int(l_val) <= int(c_reg_exp):
                            c_err = 0
                    elif c_comp == ">~":
                        # TODO check l_val and c_reg_exp if they could transformed into int
                        if int(l_val) > int(c_reg_exp_a) or re.search(c_reg_exp_b, l_val):
                            c_err = 0
                    elif c_comp == "is not" and c_reg_exp == "None":
                        c_err = 0
                    elif c_comp == "is" and c_reg_exp == "Any":
                        c_err = 0
                else:
                    # l_val is None
                    if c_comp == "is" and c_reg_exp == "None":
                        found = True   # found set True (here negative logic, so missing attribute is matching 'None', means the missing attribute has been found :)
                        c_err = 0
                        check_result = max(check_result, 0)
                    elif c_comp == "!=" and c_reg_exp != "None":
                        found = True   # found set True (here negative logic, so missing attribute is not matching c_reg_exp and c_reg_exp is not None, means the missing attribute has been found :)
                        c_err = 0
                        check_result = max(check_result, 0)
            else:
                # if object does not even exist, the 'None' clause is true
                if c_comp == "is" and c_reg_exp == "None":
                    found = True
                    c_err = 0
                    check_result = max(check_result, 0)
            if c_err == 1:
                if not found:
                    l_val = None
                self.__add_failed__((area_name, object_name), (c_key, l_val, c_reg_exp, c_comp), fatal_check=fatal_check, fatal_name=fatal_name, list_of_failures=list_of_failures)
                self.__failed_role_counter__ += 1
                check_result = max(check_result, 1)
                self.debug(f"DEBUG: FAILED: ckey:{c_key} c_comp:{c_comp} c_reg_exp:{c_reg_exp} c_reg_exp_a:{c_reg_exp_a} c_reg_exp_b:{c_reg_exp_b}")
            else:
                check_result = max(check_result, 0)
                self.debug(f"DEBUG: PASSED: ckey:{c_key} c_comp:{c_comp} c_reg_exp:{c_reg_exp} c_reg_exp_a:{c_reg_exp_a} c_reg_exp_b:{c_reg_exp_b}")
        if c_comp == "is" and c_reg_exp == "None":
            # if area does not even exist, the 'None' clause is true
            found = True
            c_err = 0
            check_result = max(check_result, 0)
        if (found is False) and (check_result < 2):
            check_result = 2
        return check_result

    def run_checks(self, checks, area_name, object_name, step_step, **kwargs ):
        """ run all checks for area and object
            params:
                   checks: list of checks to be run
                   area_name: attribute area to be checked (global, Site, Resource, Host)
                   object_name: aobject inside area to be checked (ROT, WDF, pizbuin01)
                   step_step: TBD
        """
        list_of_failures = kwargs.get('list_of_failures', None)
        fail_msg = "MISSED"
        fatal_check = kwargs.get('fatal_check', False)
        fatal_name = kwargs.get('fatal_name', "")
        check_result = -1
        if fatal_check is False:
            self.__reset_failed__()
        for single_check in checks:
            check_result = max(check_result, self.__run_check__(single_check, area_name, object_name, step_step, fatal_check=fatal_check, fatal_name=fatal_name, list_of_failures=list_of_failures))
        if fatal_check is False:
            if self.config['dump_failures'] and 'failed' in self.run:
                self.message(f"{fail_msg}: step={step_step} {self.__get_failed__()}", stdout=False)
        return check_result

    def process_topology_object(self, step, topology_object_name, area_name, **kwargs):
        """ process_topology_object
            params: step, topology_object_name, area_name
            kwargs: step_loop_failures[]
        """
        rc_checks = -1
        list_of_failures = kwargs.get('list_of_failures', None)
        if topology_object_name in step:
            checks = step[topology_object_name]
            if isinstance(checks,str):
                check_ptr = checks
                self.debug(f"DEBUG: check_ptr {check_ptr}", stdout=False)
                try:
                    checks = self.test_data["checkPtr"][check_ptr]
                except KeyError:
                    self.message(f"ERROR: Pointer {check_ptr} for {area_name} is not defined")
                    return 1
            topolo = self.topolo
            if topology_object_name in topolo:
                object_name = topolo[topology_object_name]
                rc_checks = self.run_checks(checks, area_name, object_name, step.get('step',''), list_of_failures=list_of_failures)
        return rc_checks

    def __process_fatal_condition(self, step, **kwargs):
        """ __process_fatal_conditions
            rc == 0 : no fatal condition matched
            rc != 0 : at least one of the fatal packages (childs) matched
            kwargs: step_loop_failures[]
        """
        rc_condition = 1
        list_of_failures = kwargs.get('list_of_failures', None)
        if "fatalCondition" in step:
            fc = step["fatalCondition"]
            topolo = self.topolo
            self.debug(f"DEBUG: TOPOLO {topolo}")
            #
            # process all fatalCondition childs
            #
            for child in fc:
                self.__reset_failed__()
                rc_child = 1
                #
                # process only childs which are not reserved
                #
                if child not in ['next','comment','name']:
                    fc_child = fc[child]
                    self.debug(f"DEBUG: fatalConditions: {child} dump {fc_child}")
                    #
                    # process all check-rules ( "name": [ "condition1" {,...} ] )
                    #
                    rc_child = 0
                    for top_obj_name in fc_child:
                        obj_name = topolo[top_obj_name]
                        if top_obj_name in self.topo_translate:
                            area_name = self.topo_translate[top_obj_name]
                            checks = fc_child[top_obj_name]
                            self.debug(f"DEBUG: fatalConditions: area_name {area_name}, top_obj_name {top_obj_name}, obj_name {obj_name}, checks {checks}")
                            rc_checks = self.run_checks(checks, area_name, obj_name, step.get('step',''), fatal_check = True, fatal_name=child, list_of_failures=list_of_failures)
                            self.debug(f"DEBUG: fatalConditions: {child} rc {rc_checks}")
                            rc_child = max(rc_child, rc_checks)
                if rc_child == 0:
                    self.message(f"STATUS: fatalConditions: FAILED {child} {fc_child}", pre_cr=True)
                rc_condition = min(rc_condition, rc_child)
        return rc_condition


    def process_step(self, step, **kargs):
        """ process a single step including optional loops """
        connect_host = kargs.get('connect_hosts', None)
        step_id = step['step']
        step_name = step['name']
        step_next = step['next']
        step_alternative = step.get('onfail', None)
        date_time = time.strftime("%Y-%m-%d %H:%M:%S")
        step_result = { 'start_time': date_time }
        steps_result_dict = self.result.get('steps', {})
        steps_result_dict.update({step_id: step_result})
        self.result.update({'steps': steps_result_dict})
        # self.result.update({ step_id: { 'name': step_name, 'next': step_next, 'status': 'running' } } )
        step_result.update({ 'name': step_name, 'next': step_next, 'status': 'running' })
        if 'loop' in step:
            max_loops = step['loop']
        else:
            max_loops = 1
        if 'wait' in step:
            wait = step['wait']
        else:
            wait = 2
        loops = 0
        if 'post' in step:
            step_action = step['post']
        else:
            step_action = ""
        _l_msg = (
                     "PROC:"
                     f" step_id='{step_id}'"
                     f" step_name='{step_name}'"
                     f" step_next='{step_next}'"
                     f" step_action='{step_action}'"
                     f" max_loops='{max_loops}'"
                 )
        self.message(_l_msg)
        fatal = False
        self.__min_failed_role_counter__ = 1000
        self.__max_failed_role_counter__ = 0
        step_loops = [ ]
        while loops < max_loops:
            self.__failed_role_counter__ = 0
            loops = loops + 1
            date_time = time.strftime("%Y-%m-%d %H:%M:%S")
            step_loop = { loops: {'time': date_time} }
            step_loops.append(step_loop)
            self.step_loops = step_loops
            list_of_failures = []
            step_loop.update({'failures': list_of_failures})
            if self.config['dump_failures']:
                print(".", end='', flush=True)
            process_result = -1
            self.read_saphana_sr(connect_host = connect_host)
            if "fatalCondition" in step:
                # self.message("STATUS: step {} to process fatalCondition".format(step_id))
                process_result = self.__process_fatal_condition(step)
                self.debug(f"DEBUG: step {step_id} to processed fatalCondition with process_result {process_result}")
                if process_result == 0:
                    self.message("STATUS: step {} failed with fatalCondition - BREAK".format(step_id))
                    process_result = 2
                    fatal = True
                    break
            process_result = max (
                                  self.process_topology_object(step, 'global', 'Global', list_of_failures=list_of_failures),
                                  self.process_topology_object(step, 'mstRsc', 'Resource', list_of_failures=list_of_failures),
                                  self.process_topology_object(step, 'pSite', 'Site', list_of_failures=list_of_failures),
                                  self.process_topology_object(step, 'sSite', 'Site', list_of_failures=list_of_failures),
                                  self.process_topology_object(step, 'pHost', 'Host', list_of_failures=list_of_failures),
                                  self.process_topology_object(step, 'sHost', 'Host', list_of_failures=list_of_failures),
                                  self.process_topology_object(step, 'pWorker', 'Host', list_of_failures=list_of_failures),
                                  self.process_topology_object(step, 'sWorker', 'Host', list_of_failures=list_of_failures),
                                  self.process_topology_object(step, 'pWorker2', 'Host', list_of_failures=list_of_failures),
                                  self.process_topology_object(step, 'sWorker2', 'Host', list_of_failures=list_of_failures),
                                  self.process_topology_object(step, 'tSite', 'Site', list_of_failures=list_of_failures),
                                  self.process_topology_object(step, 'fSite', 'Site', list_of_failures=list_of_failures),
                                  self.process_topology_object(step, 'tHost', 'Host', list_of_failures=list_of_failures),
                                  self.process_topology_object(step, 'fHost', 'Host', list_of_failures=list_of_failures),
                                 )
            if process_result == 0:
                break
            self.__min_failed_role_counter__ = min(self.__min_failed_role_counter__, self.__failed_role_counter__)
            self.__max_failed_role_counter__ = max(self.__max_failed_role_counter__, self.__failed_role_counter__)
            self.message(f"MISSED: step {step_id} role-fail-counter: {self.__failed_role_counter__} (min: {self.__min_failed_role_counter__} max: {self.__max_failed_role_counter__})", stdout=False)
            time.sleep(wait)
        if self.__min_failed_role_counter__ == 1000:
            self.__min_failed_role_counter__ = 0
        step_result.update({'loops_needed': loops, 'loops_allowed': max_loops, 'min_fail': self.__min_failed_role_counter__, 'max_fail': self.__max_failed_role_counter__})
        date_time = time.strftime("%Y-%m-%d %H:%M:%S")
        step_result.update({ 'end_time': date_time })
        if self.config['dump_failures'] and fatal is False:
            print("")
        self.message("STATUS: step {} checked in {} loop(s)".format(step_id, loops))
        if process_result == 0:
            if len(step_action) != 0:
                action_rc = self.action(step_action) # post-action is only called, if step checks have been passed
                step_result.update({'action': step_action})
                step_result.update({'action_rc': action_rc})
                if action_rc != 0:
                    process_result = 1 # set step failed, if post-action failed

        if process_result == 0:
            step_result.update({ 'status': 'passed' })

        else:
            if step_alternative:
                step_result.update({ 'status': 'alternative/on_fail' })
            else:
                step_result.update({ 'status': 'failed' })
                step_result.update({ 'loops': step_loops })  # for failed steps also report the loops and their failures
        # self.result.update({step_id: step_result})
        return process_result

    def process_steps(self, **kargs):
        """ process a seria of steps till next-step is "END" or there is no next-step """
        connect_host = kargs.get('connect_hosts', None)
        test_start = self.test_data['start']
        step=self.get_step(test_start)
        step_step = step['step']
        r_code = 0
        # onfail for FIRST step is 'break' - break, if INITIAL step fails
        onfail = 'break'
        while step_step != "END":
            step_next = step['next']
            #
            # prepare an 'alternative' step sequence, if 'alternative/on_fail' is set for this step
            #
            step_alternative = step.get('onfail', None)
            process_result = self.process_step(step, connect_host = connect_host)
            if process_result == 0:
                self.message("STATUS: Test step {} PASSED successfully".format(step_step))
                step=self.get_step(step_next)
            else:
                r_code = 1
                self.message("STATUS: Test step {} FAILED successfully ;)".format(step_step))
                # TODO: add onfail handling
                # (curently only break for first step and continue for others)
                if onfail == 'break':
                    break
                # in case there is no break, we continue with ...
                if step_alternative:
                    # process alternative test steps, so reset the failed test rc_code
                    r_code = 0
                    step=self.get_step(step_alternative)
                else:
                    step=self.get_step(step_next)
            if step:
                step_step = step['step']
            else:
                # check, why we run into this code path
                break
            # onfail for ALL NEXT steps is based on the on_fail_reaction command line option, default is 'continue' to run also the recovery steps
            onfail_reaction = self.config.get('on_fail_reaction', 'continue')
            if onfail_reaction == 'exit':
                onfail = 'break'
            else:
                onfail = 'continue'
        return r_code

    def process_test(self, **kargs):
        """ process the entire test defined in test_data """
        connect_host = kargs.get('connect_host', None)
        self.run['test_id'] = self.test_data['test']
        test_id = self.run['test_id']
        test_name = self.test_data['name']
        test_start = self.test_data['start']
        test_sid = self.test_data['sid']
        test_resource = self.test_data['mstResource']
        _l_run = self.run
        _l_msg = "PROC:"
        _l_msg += f" test_id='{test_id}'"
        _l_msg += f" test_sid='{test_sid}'"
        _l_msg += f" test_name='{test_name}'"
        _l_msg += f" test_start='{test_start}'"
        _l_msg += f" test_resource='{test_resource}'"
        self.message(_l_msg)
        r_code = self.process_steps(connect_host = connect_host )
        return r_code

    def get_step(self, step_name):
        """ query for a given step with step_name in test_data """
        step = None
        for step_element in self.test_data['steps']:
            if step_element['step'] == step_name:
                step = step_element
                break
        return step

    def action_call(self, action_name, cmd, remote, **kargs):
        """ do the action itself """
        ignore = kargs.get('ignore', False) # optionally "ignore" a rc!=0 and translate the rc to 0 (zero)
        action_rc = 0
        if cmd != "":
            if remote == "localhost":
                self.message("ACTION: {} LOCAL: {}".format(action_name, cmd))
                local_call_result = subprocess.run(cmd.split(), check=False)
                action_rc = local_call_result.returncode
                self.message("ACTION: {} LOCAL: {} rc={}".format(action_name, cmd, action_rc))
            else:
                self.message("ACTION: {} REMOTE at {}: {}".format(action_name, remote, cmd))
                a_result = self.__do_ssh__(remote, self.config['user'], cmd, password=self.config['password'], log=True)
                action_rc = a_result[2]
                self.message("ACTION: {} REMOTE at {}: {} rc={}".format(action_name, remote, cmd, action_rc))
        if ignore:
            self.message(f"INFO: ignore rc={action_rc} (ignore=True)")
            action_rc = 0
        return action_rc

    def action_on_hana(self, action_name, **kargs):
        """ perform a given action on SAP HANA primary or secondary """
        ha_or_dr = kargs.get('ha_or_dr', 'HA')
        the_action = kargs.get('action', None)
        ref_sHost = 'sHost'
        ref_pHost = 'pHost'
        ref_sWorker = 'sWorker'
        ref_pWorker = 'pWorker'
        #ref_sWorker2 = 'sWorker2'
        #ref_pWorker2 = 'pWorker2'
        if ha_or_dr == "DR":
            ref_sHost = 'fHost'
            ref_pHost = 'tHost'
            ref_sWorker = 'fWorker'
            ref_pWorker = 'tWorker'
        remote = self.config['remote_node']
        test_sid = self.test_data['sid']
        test_ino = self.test_data['instNo']
        cmd = ""
        sudo_cmd = ""
        ignore = False
        if action_name in ("kill_secn_inst", "kill_fourth_inst"): # either second of HA or DR region
            remote = self.topolo[ref_sHost]
            cmd = "su - {}adm HDB kill-9".format(test_sid.lower())
            sudo_cmd = "sudo -u {}adm --login /usr/sap/{}/HDB{}/HDB kill-9".format(test_sid.lower(), test_sid, test_ino)
        elif action_name == "kill_secn_worker_inst":
            remote = self.topolo[ref_sWorker]
            cmd = "su - {}adm HDB kill-9".format(test_sid.lower())
            sudo_cmd = "sudo -u {}adm --login /usr/sap/{}/HDB{}/HDB kill-9".format(test_sid.lower(), test_sid, test_ino)
        elif action_name in ("kill_prim_inst", "kill_third_inst"): # either first of HA or DR region
            remote = self.topolo[ref_pHost]
            cmd = "su - {}adm HDB kill-9".format(test_sid.lower())
            sudo_cmd = "sudo -u {}adm --login /usr/sap/{}/HDB{}/HDB kill-9".format(test_sid.lower(), test_sid, test_ino)
        elif action_name == "kill_prim_worker_inst":
            remote = self.topolo[ref_pWorker]
            cmd = "su - {}adm HDB kill-9".format(test_sid.lower())
            sudo_cmd = "sudo -u {}adm --login /usr/sap/{}/HDB{}/HDB kill-9".format(test_sid.lower(), test_sid, test_ino)
        elif action_name == "kill_prim_indexserver":
            remote = self.topolo[ref_pHost]
            cmd = "pkill -u {}adm --signal 11 hdbindexserver".format(test_sid.lower())
            sudo_cmd = "sudo -u root pkill -u {}adm --signal 11 hdbindexserver".format(test_sid.lower())
        elif action_name == "kill_secn_indexserver":
            remote = self.topolo[ref_sHost]
            cmd = "pkill -u {}adm --signal 11 hdbindexserver".format(test_sid.lower())
            sudo_cmd = "sudo -u root pkill -u {}adm --signal 11 hdbindexserver".format(test_sid.lower())
        elif action_name == "kill_prim_worker_indexserver":
            remote = self.topolo[ref_pWorker]
            cmd = "pkill -u {}adm --signal 11 hdbindexserver".format(test_sid.lower())
            sudo_cmd = "sudo -u root pkill -u {}adm --signal 11 hdbindexserver".format(test_sid.lower())
        elif action_name == "kill_secn_worker_indexserver":
            remote = self.topolo[ref_sWorker]
            cmd = "pkill -u {}adm --signal 11 hdbindexserver".format(test_sid.lower())
            sudo_cmd = "sudo -u root pkill -u {}adm --signal 11 hdbindexserver".format(test_sid.lower())
        elif action_name == "kill_prim_xsengine":
            remote = self.topolo[ref_pHost]
            cmd = "pkill -u {}adm --signal 11 hdbxsengine".format(test_sid.lower())
            sudo_cmd = "sudo -u root pkill -u {}adm --signal 11 hdbxsengine".format(test_sid.lower())
        elif action_name == "kill_secn_xsengine":
            remote = self.topolo[ref_sHost]
            cmd = "pkill -u {}adm --signal 11 hdbxsengine".format(test_sid.lower())
            sudo_cmd = "sudo -u root pkill -u {}adm --signal 11 hdbxsengine".format(test_sid.lower())
        elif action_name == "kill_prim_nameserver":
            remote = self.topolo[ref_pHost]
            cmd = "pkill -u {}adm --signal 11 hdbnameserver".format(test_sid.lower())
            sudo_cmd = "sudo -u root pkill -u {}adm --signal 11 hdbnameserver".format(test_sid.lower())
        elif action_name == "kill_secn_nameserver":
            remote = self.topolo[ref_sHost]
            cmd = "pkill -u {}adm --signal 11 hdbnameserver".format(test_sid.lower())
            sudo_cmd = "sudo -u root pkill -u {}adm --signal 11 hdbnameserver".format(test_sid.lower())
        elif action_name == "bmt":
            remote = self.topolo[ref_sHost]
            cmd = "su - {}adm -c 'hdbnsutil -sr_takeover'".format(test_sid.lower())
            sudo_cmd = "sudo -u {}adm --login /usr/sap/{}/HDB{}/exe/hdbnsutil -sr_takeover".format(test_sid.lower(), test_sid, test_ino)
            ignore = True  # ignore rc!=0, because this is intended for this case
        if self.config['use_sudo']:
            cmd = sudo_cmd
        return self.action_call(action_name, cmd, remote, ignore=ignore)

    def action_on_cluster(self, action_name, **kargs):
        """ perform a given action on cluster node """
        #ha_or_dr = kargs.get('ha_or_dr', 'HA')
        the_action = kargs.get('action', None)
        the_node = None
        the_node_type = None
        the_connection = None
        remote = self.config['remote_node']
        resource = self.test_data['mstResource']
        cmd = ""
        sudo_cmd = ""
        if the_action:
            the_node_type = the_action.get('node', None)
        if the_node_type:
            the_node = self.topolo.get(the_node_type, None)
            remote = the_node
        else:
            the_connection = the_action.get('connection', None)
            if the_connection:
                if the_connection == 'local':
                    remote = 'localhost'   # overwrite remote to localhost
        self.message(f"INFO: the_node_type: {the_node_type}, the_node: {the_node}, the_connection: {the_connection} remote: {remote}") # TODO: change to debug later
        if action_name in ("ssn", "standby_secn_node", "standby_fourth_node"):
            cmd = f"/usr/sbin/crm node standby {the_node}"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name in ("osn", "online_secn_node", "online_fourth_node"):
            cmd = f"/usr/sbin/crm node online {the_node}"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name in ("spn", "standby_prim_node", "standby_third_node"):
            cmd = f"/usr/sbin/crm node standby {the_node}"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name in ("opn", "online_prim_node", "online_third_node"):
            cmd = f"/usr/sbin/crm node online {the_node}"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name == "standby_prim_worker_node":
            cmd = f"/usr/sbin/crm node standby {the_node}"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name == "online_prim_worker_node":
            cmd = f"/usr/sbin/crm node online {the_node}"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name == "standby_secn_worker_node":
            cmd = f"/usr/sbin/crm node standby {the_node}"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name == "online_secn_worker_node":
            cmd = f"/usr/sbin/crm node online {the_node}"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name == "cleanup":
            cmd = f"/usr/sbin/crm resource cleanup {resource}"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name == "kill_secn_worker_node":
            remote = the_node
            cmd = "/usr/bin/systemctl reboot --force"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name == "kill_secn_worker2_node":
            remote = the_node
            cmd = "/usr/bin/systemctl reboot --force"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name in ("kill_secn_node", "kill_fourth_node"): # either second of HA or DR region
            remote = the_node
            cmd = "/usr/bin/systemctl reboot --force"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name == "kill_prim_worker_node":
            remote = the_node
            cmd = "/usr/bin/systemctl reboot --force"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name in ("kill_prim_node", "kill_third_node"): # either first of HA or DR region
            remote = the_node
            cmd = "/usr/bin/systemctl reboot --force"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name == "simulate_split_brain":
            remote = the_node
            # TODO: not ready for DRregion
            cmd = f"/usr/bin/iptables -I INPUT -s {self.topolo.get('pHost')} -j DROP"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name == "start_hana_resource":
            remote = the_node
            cmd = f"crm resource start {resource}"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name == "stop_hana_resource":
            remote = the_node
            cmd = f"crm resource stop {resource}"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name == "ban_prim_hana_resource":
            remote = the_node
            cmd = f"crm resource ban {resource}"
            sudo_cmd = f"sudo -u root {cmd}"
        elif action_name == "ban_secn_hana_resource":
            remote = the_node
            cmd = f"crm resource ban {resource}"
            sudo_cmd = f"sudo -u root {cmd}"
        if self.config['use_sudo']:
            cmd = sudo_cmd
        return self.action_call(action_name, cmd, remote)

    def action_on_os(self, action_name, **kargs):
        """ perform a given action on control node """
        the_action = kargs.get('action', None)
        remote = self.config['remote_node']
        action_array = action_name.split(" ")
        action_name_short = action_array[0]

        sid = self.test_data['sid'].lower()
        SID = self.test_data['sid'].upper()
        ino = self.test_data['instNo']
        pHost = self.topolo.get('pHost', None)
        mst_resource = self.test_data.get('mstResource','')

        action_type_name = the_action.get('action_type', {})
        the_action_type = self.action_types.get(action_type_name)

        cmd = the_action_type.get('cmd', "")
        sudo = the_action_type.get('sudo', "")
        node = the_action.get('node', "")
        param1 = the_action.get('param1', "")
        param2 = the_action.get('param2', "")

        replace = {
                    '@@actParam1@@': action_array[1],
                    '@@actParamAll@@': " ".join(action_array[0:]),
                    '@@cmd@@': cmd,
                    '@@INO@@': ino,
                    '@@mst_resource@@': mst_resource,
                    '@@node@@': node,
                    '@@param1@@': param1,
                    '@@param2@@': param2,
                    '@@pHost@@': pHost,
                    # '@@service@@': xxTODOxx,
                    '@@sid@@': sid,
                    '@@SID@@': SID
                  }

        self.message(f'INFO: replace: {replace}')
        self.message(f'INFO: cmd (before): {cmd}')

        cmd = self.__resolve__(cmd, replace = replace)
        replace.update({ 'cmd': cmd })
        self.message(f'INFO: cmd (after): {cmd}')

        sudo = self.__resolve__(sudo,  replace = replace)

        if action_name_short == "sleep":
            remote = 'localhost'
            if len(action_array) == 2:
                action_parameter = action_array[1]
            else:
                action_parameter = "60"
            cmd = "sleep {}".format(action_parameter)
        elif action_name_short == "shell":
            remote = 'localhost'
            action_parameter = " ".join(action_array[1:])
            cmd = "{}".format(action_parameter)
        return self.action_call(action_name, cmd, remote)

    def action(self, action_name):
        """ perform a given action """
        action_array = action_name.split(" ")
        action_name_short = action_array[0]
        action_rc = 0
        if action_name == "":
            action_rc = 0
        else:
            the_action = self.actions.get(action_name_short, None)
            the_type = "n/a"
            if the_action:
                the_type = the_action.get('type', "n/a")
            if the_type == 'hana':
                hadr = the_action.get('ha_dr', None)
                self.message(f"INFO: Use action dictionary to identify action type 'hana' for action '{action_name_short}'")
                action_rc = self.action_on_hana(action_name, ha_or_dr=hadr, action=the_action)
            elif the_type == 'cluster':
                hadr = the_action.get('ha_dr', None)
                self.message(f"INFO: Use action dictionary to identify action type 'cluster' for action '{action_name_short}'")
                action_rc = self.action_on_cluster(action_name, ha_or_dr=hadr, action=the_action)
            elif the_type == 'os':
                self.message(f"INFO: Use action dictionary to identify action type 'os' for action '{action_name_short}'")
                action_rc = self.action_on_os(action_name, action=the_action)
            else:
                action_rc = 2
        return action_rc

    def query_call(self, action_name, cmd, remote):
        """ do the query itself """
        # result = []
        action_stdout = ""
        if cmd != "":
            if remote == "localhost":
                self.message("QUERY: {} LOCAL: {}".format(action_name, cmd))
                local_call_result = subprocess.run(cmd.split(), check=False, capture_output=True)
                action_rc = local_call_result.returncode
                action_stdout = local_call_result.stdout
                self.message("QUERY: {} LOCAL: {} rc={} ({})".format(action_name, cmd, action_rc, action_stdout))
            else:
                self.message("QUERY: {} REMOTE at {}: {}".format(action_name, remote, cmd))
                a_result = self.__do_ssh__(remote, self.config['user'], cmd, password=self.config['password'], log=True)
                action_rc = a_result[2]
                action_stdout = a_result[0]
                self.message("QUERY: {} REMOTE at {}: {} rc={}".format(action_name, remote, cmd, action_rc))
        return [action_stdout, None, action_rc]

    def query_on_cluster(self, action_name):
        """ query_on_cluster - do a query on cluster aspects (like list_nodes) """
        remote = self.config['remote_node']
        cmd = ""
        sudo_cmd = ""
        if action_name == "list_nodes":
            cmd = "/usr/sbin/crm_node --list"
            sudo_cmd = f"sudo -u root {cmd}"
        if self.config['use_sudo']:
            cmd = sudo_cmd
        return self.query_call(action_name, cmd, remote)

    def query(self, action_name):
        """ perform a given query (also give-back stdout) query_result : [stdout, stdin, rc] """
        query_result = None
        if action_name in ("list_nodes"):
            query_result = self.query_on_cluster(action_name)
        return query_result

    def __do_ssh__(self, remote_host, user, cmd, **kwargs):
        """
        ssh remote cmd exectution
        returns a tuple ( stdout-string, stderr, string, rc )
        """
        ssh_timeout = kwargs.get('timeout', None)
        ssh_password = kwargs.get('password', None)
        do_log = kwargs.get('log', False)
        if remote_host:
            ssh_client = paramiko.SSHClient()
            ssh_client.load_system_host_keys()
            try:
                if not self.config ['check_host']:
                    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                if ssh_password:
                    ssh_client.connect(remote_host, username=user, password=ssh_password, timeout=10)
                else:
                    ssh_client.connect(remote_host, username=user, timeout=10)
            except Exception as e:
                self.message(f"FAILURE: ssh connection to failed - ({e})")
                check_result=("", "", 20000)
            self.debug(f"DEBUG: ssh cmd '{cmd}' timeout={ssh_timeout}")
            if do_log:
                if ssh_timeout:
                    self.message(f"CALL: ssh cmd '{cmd}' timeout={ssh_timeout}")
                else:
                    self.message(f"CALL: ssh cmd '{cmd}'")
            try:
                if ssh_timeout:
                    (cmd_stdout, cmd_stderr) = ssh_client.exec_command(cmd, timeout=ssh_timeout)[1:]
                else:
                    (cmd_stdout, cmd_stderr) = ssh_client.exec_command(cmd)[1:]
                result_stdout = cmd_stdout.read().decode("utf8")
                result_stderr = cmd_stderr.read().decode("utf8")
                result_rc = cmd_stdout.channel.recv_exit_status()
                check_result = (result_stdout, result_stderr, result_rc)
                ssh_client.close()
                self.debug(f"DEBUG: ssh cmd '{cmd}' {user}@{remote_host}: return code {result_rc}")
                if do_log:
                    self.message(f"CALL: ssh cmd '{cmd}' {user}@{remote_host}: return code {result_rc}")
            except Exception as e:
                self.message(f"FAILURE: ssh connection to failed - ({e})")
                check_result=("", "", 20000)
        else:
            self.message("FAILURE: ssh connection to failed - remote_host not specified")
            check_result=("", "", 20000)
        return check_result

if __name__ == "__main__":
    test01 = SaphanasrTest()
    while test01.run['count'] <= test01.config['repeat']:
        test01.run['r_id'] = random.randrange(10000,99999,1)
        test01.read_saphana_sr()
        l_top = test01.topolo
        # l_top.update({'global': 'global'})
        # for angi-ScaleUp and classic ScaleOut:
        # pSite is the site with srr-attribute == "P"
        # sSite is the site with srr-attribute == "S"
        # pHost is the host with site-attribute == pSite
        # sHost is the host with site-attribute == sSite
        # TODO: for angi-ScaleOut and classic-ScaleOut we might need to differ msn-host, plain-worker (no mns-candidate) and standby node
        # TODO: classic-ScaleUp
        # pHost could be the host with roles-attr like [0-4]:P:*
        # sHost could be the host with roles-attr like [0-4]:S:*
        # pSite is referenced by pHost-site-attr
        # sSite is referenced by sHost-site-attr
        #
        l_top.update({'pSite': test01.get_area_object_by_key_val('Site', { 'srr': 'P'})})
        l_top.update({'sSite': test01.get_area_object_by_key_val('Site', { 'srr': 'S'})})
        # first try to use site-msn attribute to get the master name server
        # TODO: check, if msn could be 'misleading', if using 'virtual' SAP HANA host names
        l_top.update({'pHost': test01.get_value('Site', l_top['pSite'], 'mns')})
        l_top.update({'sHost': test01.get_value('Site', l_top['sSite'], 'mns')})

        test01.debug(f"DEBUG: get 'other' worker - {test01.get_area_object_by_key_val('Host', { 'roles': ':worker:slave'}, sloppy=True)}")

        if l_top['pHost'] is None:
            # if mns attributes do not work this is most likely a classic-ScaleUp we need to query by roles
            l_top.update({'pHost': test01.get_area_object_by_key_val('Host', {'roles': '[0-4]:P:'}, sloppy=True)})
            l_top.update({'sHost': test01.get_area_object_by_key_val('Host', {'roles': '[0-4]:S:'}, sloppy=True)})
            l_top.update({'pSite': test01.get_value('Host', l_top['pHost'], 'site')})
            l_top.update({'sSite': test01.get_value('Host', l_top['sHost'], 'site')})

        #
        # now add special resources to topology for later use in process_step
        #
        l_top.update({'mstRsc': test01.get_value('Host', l_top['sHost'], 'site')})

        # TODO: do we need the old method as fallback, if msn is empty or misleading?
        #l_top.update({'pHost': test01.get_area_object_by_key_val('Host', 'site', l_top['pSite'])})
        #l_top.update({'sHost': test01.get_area_object_by_key_val('Host', 'site', l_top['sSite'])})
        l_msg = (
                    f"TOPO: pSite={l_top['pSite']}"
                    f" sSite={l_top['sSite']}"
                    f" pHost={l_top['pHost']}"
                    f" sHost={l_top['sHost']}"
                )
        test01.result.update({'topology': l_top, 'testtag': 'test25' })
        test01.message(l_msg)
        test01.read_test_file()
        my_test_id = test01.run['test_id']
        if test01.config['repeat'] != 1:
            test01.message("TEST: {} testNr={} ######".format(my_test_id, test01.run['count']))
        test01.run['test_rc'] = test01.process_test()
        msg_templ = "TEST: {} testNr={} {} successfully :) ######"
        if test01.run['test_rc'] == 0:
            test01.message(msg_templ.format(my_test_id, 'PASSED', test01.run['count']))
        else:
            test01.message(msg_templ.format(my_test_id, 'FAILED', test01.run['count']))
        test01.run['count'] += 1
    if  test01.run['log_file_handle']:
        test01.run['log_file_handle'].close()
