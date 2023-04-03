# pylint: disable=consider-using-f-string
# pylint: disable=C0301
"""
 saphanasrtest.py
 Author:       Fabian Herschel, Mar 2023
 License:      GNU General Public License (GPL)
 Copyright:    (c) 2023 SUSE LLC
"""

import time
#import subprocess
import re
import sys
import json
import argparse
import random

# for ssh remote calls this module uses paramiko
from paramiko import SSHClient

class SaphanasrTest:
    """
    class to check SAP HANA cluster during tests
    """
    version = "0.1.20230403.1736-lint18"

    def message(self, msg):
        """
        message with formatted timestamp
        """
        # TODO: specify, if message should be written to stdout, stderr and/or log file
        date_time = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.r_id:
            r_id = " [{}]".format(self.r_id)
        else:
            r_id = ""
        msg_arr = msg.split(" ")
        print("{}{} {:<9s} {}".format(date_time, r_id, msg_arr[0], " ".join(msg_arr[1:])))
        try:
            self.message_fh(msg, self.log_file_handle)
        except OSError:
            print("{0} {1:<9s} {2}".format(date_time, "ERROR:", "Could not write log log file"))

    def message_fh(self, msg, file_handle):
        """ print a message with fotmatted timestamp to a file handle """
        date_time = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.r_id:
            r_id = " [{}]".format(self.r_id)
        else:
            r_id = ""
        msg_arr = msg.split(" ")
        if file_handle:
            file_handle.write("{}{} {:<9s} {}\n".format(date_time, r_id, msg_arr[0], " ".join(msg_arr[1:])))

    def __init__(self, *args):
        """
        constructor
        """
        self.log_file_handle = None
        self.r_id = None
        self.message("INIT: {}".format(self.version))
        self.config = { 'test_file': "-", 'defaults_checks_file': None, 'properties_file': "properties.json", 'log_file': "", 'repeat': 1, 'dump_failures': False, 'remote_node': None }
        self.dict_sr = {}
        self.test_data = {}
        self.properties_file = "properties.json"
        self.log_file = ""
        self.repeat = 1
        self.dump_failures = False
        self.topolo = { 'pSite': None, 'sSite': None, 'pHost': None, 'sHost': None }
        self.remote_node = None
        self.test_rc = 0
        self.count = 1
        parser = argparse.ArgumentParser()
        parser.add_argument("--testFile", help="specify the test file")
        parser.add_argument("--defaultChecksFile", help="specify the default checks file")
        parser.add_argument("--properties", help="specify the properties file")
        parser.add_argument("--remoteNode", help="cluster node to use for ssh connection")
        parser.add_argument("--simulate", help="only simulate, dont call actions", action="store_true")
        parser.add_argument("--repeat", help="how often to repeat the test")
        parser.add_argument("--dumpFailures", help="print failed checks per loop", action="store_true")
        parser.add_argument("--logFile", help="log file to write the messages")
        args = parser.parse_args()
        if args.testFile:
            self.message("PARAM: testFile: {}".format(args.testFile))
            self.config['test_file'] = args.testFile
        if args.defaultChecksFile:
            self.message("PARAM: defaultChecksFile: {}".format(args.defaultChecksFile))
            self.config['defaults_checks_file'] = args.defaultChecksFile
        if args.properties:
            self.message("PARAM: properties: {}".format(args.properties))
            self.properties_file = args.properties
        if args.remoteNode:
            self.message("PARAM: remoteNode: {}".format(args.remoteNode))
            self.remote_node = args.remoteNode
        if args.repeat:
            self.message("PARAM: repeat: {}".format(args.repeat))
            self.repeat = int(args.repeat)
        if args.dumpFailures:
            self.message("PARAM: dumpFailures")
            self.dump_failures = args.dumpFailures
        if args.logFile:
            self.message("PARAM: logFile: {}".format(args.logFile))
            self.log_file = args.logFile
            self.log_file_handle = open(self.log_file, 'a', encoding="utf-8")
        random.seed()

    def insert_to_area(self, area, the_object):
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

    def get_object(self, area, object_name):
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

    def insert_to_object(self, the_object, key, value):
        """ insert a key-value pair into the object dictionary """
        l_obj = the_object
        l_dic = { key: value }
        l_obj.update(l_dic)
        return l_obj

    def read_saphana_sr(self):
        """ method to read SAPHanaSR-showAttr cluster attributes and create a nested dictionary structure representing the data """
        #cmd = [ './helpSAPHanaSR-showAttr', '--format=script'  ]
        cmd = "SAPHanaSR-showAttr --format=script"
        self.dict_sr={}
        result_sr = self.do_ssh(self.remote_node, "root", cmd)
        for line in result_sr[0].splitlines():
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
                l_obj=self.get_object(area, object_name)
                if l_obj:
                    self.insert_to_object(l_obj,key,val)
                else:
                    l_obj = self.create_object(object_name, key, val)
                    self.insert_to_area(area, l_obj)
        return 0

    def search_in_area_for_object_by_key_value(self, area_name, key, value):
        """ method to search in SR for an ObjectName filtered by 'area' and key=value """
        object_name = None
        l_sr = self.dict_sr
        if area_name in l_sr:
            l_area = l_sr[area_name]
            for k in l_area.keys():
                l_obj = l_area[k]
                if key in l_obj:
                    if l_obj[key] == value:
                        object_name = k
                        # currently we only return the first match
                        break
        return object_name

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
        if self.properties_file:
            with open(self.properties_file, encoding="utf-8") as prop_fh:
                self.test_data.update(json.load(prop_fh))
        if self.config['defaults_checks_file']:
            with open(self.config['defaults_checks_file'], encoding="utf-8") as dc_fh:
                self.test_data.update(json.load(dc_fh))
        if self.config['test_file'] == "-":
            self.test_data.update(json.load(sys.stdin))
        else:
            with open(self.config['test_file'], encoding="utf-8") as tf_fh:
                self.test_data.update(json.load(tf_fh))
        self.message_fh("DEBUG: test_data: {}".format(str(self.test_data)),self.log_file_handle)

    def run_checks(self, checks, area_name, object_name ):
        """ run all checks for area and object """
        l_sr = self.dict_sr
        check_result = -1
        failed_checks = ""
        for single_check in checks:
            # match <key>=<regExp>
            match_obj = re.search("(.*)(=)(.*)", single_check)
            c_key = match_obj.group(1)
            #c_comp = match_obj.group(2)
            c_reg_exp = match_obj.group(3)
            found = 0
            if area_name in l_sr:
                l_area = l_sr[area_name]
                if object_name in l_area:
                    l_obj = l_area[object_name]
                    if c_key in l_obj:
                        l_val = l_obj[c_key]
                        found = 1
                        if re.search(c_reg_exp, l_val):
                            check_result = max(check_result, 0)
                        else:
                            if failed_checks == "":
                                failed_checks = "{}={}: {}={} !~ {}".format(area_name,object_name,c_key,l_val,c_reg_exp)
                            else:
                                failed_checks += "; {}={} !~ {}".format(c_key,l_val,c_reg_exp)
                            check_result = max(check_result, 1)
            if (found == 0) and (check_result < 2 ):
                check_result = 2
        if self.dump_failures and failed_checks != "":
            self.message_fh("FAILED: {}".format(failed_checks), self.log_file_handle)
        return check_result

    def process_topology_object(self, step, topology_object_name, area_name):
        """ process_topology_object """
        rc_checks = -1
        if topology_object_name in step:
            checks = step[topology_object_name]
            if isinstance(checks,str):
                check_ptr = checks
                self.message_fh("DEBUG: check_ptr {}".format(check_ptr), self.log_file_handle)
                checks = self.test_data["checkPtr"][check_ptr]
                #for c in checks:
                #    self.message("DEBUG: check_ptr {} check {}".format(check_ptr,c))
            topolo = self.topolo
            if topology_object_name in topolo:
                object_name = topolo[topology_object_name]
                rc_checks = self.run_checks(checks, area_name, object_name)
        return rc_checks

    def process_step(self, step):
        """ process a single step including optional loops """
        step_id = step['step']
        step_name = step['name']
        step_next = step['next']
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
        self.message("PROC: step_id={} step_name='{}' step_next={} step_action='{}'".format(step_id, step_name, step_next, step_action))
        while loops < max_loops:
            loops = loops + 1
            if self.dump_failures:
                print(".", end='', flush=True)
            process_result = -1
            self.read_saphana_sr()
            process_result = max ( self.process_topology_object(step, 'pSite', 'Sites'),
                                  self.process_topology_object(step, 'sSite', 'Sites'),
                                  self.process_topology_object(step, 'pHost', 'Hosts'),
                                  self.process_topology_object(step, 'sHost', 'Hosts'))
            if process_result == 0:
                break
            time.sleep(wait)
        if self.dump_failures:
            print("")
        self.message("STATUS: step {} checked in {} loop(s)".format(step_id, loops))
        if process_result == 0:
            self.action(step_action)
        return process_result

    def process_steps(self):
        """ process a seria of steps till next-step is "END" or there is no next-step """
        test_start = self.test_data['start']
        step=self.get_step(test_start)
        step_step = step['step']
        r_code = 0
        # onfail for first step is 'break'
        onfail = 'break'
        while step_step != "END":
            step_next = step['next']
            process_result = self.process_step(step)
            if process_result == 0:
                self.message("STATUS: Test step {} passed successfully".format(step_step))
            else:
                r_code = 1
                self.message("STATUS: Test step {} FAILED successfully ;-)".format(step_step))
                # TODO: add onfail handling (cuurently only brak for furst step and continue for others)
                if onfail == 'break':
                    break
            step=self.get_step(step_next)
            if step:
                step_step = step['step']
            else:
                # check, why we run into this code path
                break
            # onfail for all next steps is 'continue' to run also the recovery steps
            onfail = 'continue'
        return r_code

    def process_test(self):
        """ process the entire test defined in test_data """
        test_id = self.test_data['test']
        test_name = self.test_data['name']
        test_start = self.test_data['start']
        test_sid = self.test_data['sid']
        test_resource = self.test_data['mstResource']
        self.message("PROC: test_id={} test_name={} test_start={} test_sid={} test_res={}".format(test_id, test_name, test_start, test_sid, test_resource))
        r_code = self.process_steps()
        return r_code

    def get_step(self, step_name):
        """ query for a given step with step_name in test_data """
        step = None
        for step_element in self.test_data['steps']:
            if step_element['step'] == step_name:
                step = step_element
                break
        return step

    def action(self, action_name):
        """ perform a given action """
        remote = self.remote_node
        cmd = ""
        action_rc = 1
        # resource = "ms_SAPHanaCon_HA1_HDB00"
        test_sid = self.test_data['sid']
        resource = self.test_data['mstResource']
        action_array = action_name.split(" ")
        action_name_short = action_array[0]
        if action_name == "":
            action_rc = 0
        elif action_name == "ksi":
            remote = self.topolo['sHost']
            cmd = "su - {}adm HDB kill-9".format(test_sid.lower())
        elif action_name == "kpi":
            remote = self.topolo['pHost']
            cmd = "su - {}adm HDB kill-9".format(test_sid.lower())
        elif action_name == "kpx":
            remote = self.topolo['pHost']
            cmd = "pkill -f -u {}adm --signal 11 hdbindexserver".format(test_sid.lower())
        elif action_name == "ksx":
            remote = self.topolo['sHost']
            cmd = "pkill -f -u {}adm --signal 11 hdbindexserver".format(test_sid.lower())
        elif action_name == "bmt":
            remote = self.topolo['sHost']
            cmd = "su - {}adm -c 'hdbnsutil -sr_takeover'".format(test_sid.lower())
        elif action_name == "ssn":
            remote = self.remote_node
            cmd = "crm node standby {}".format(self.topolo['sHost'])
        elif action_name == "osn":
            remote = self.remote_node
            cmd = "crm node online {}".format(self.topolo['sHost'])
        elif action_name == "spn":
            remote = self.remote_node
            cmd = "crm node standby {}".format(self.topolo['pHost'])
        elif action_name == "opn":
            remote = self.remote_node
            cmd = "crm node online {}".format(self.topolo['pHost'])
        elif action_name == "cleanup":
            # TODO: get resource name from test_data
            remote = self.remote_node
            cmd = "crm resource cleanup {}".format(resource)
        elif action_name_short == "sleep":
            remote = self.remote_node
            if len(action_array) == 2:
                action_parameter = action_array[1]
            else:
                action_parameter = "60"
            cmd = "sleep {}".format(action_parameter)
        elif action_name_short == "shell":
            remote = 'localhost'
            action_parameter = " ".join(action_array[1:])
            cmd = "bash {}".format(action_parameter)
        if cmd != "":
            self.message("ACTION: {} at {}: {}".format(action_name, remote, cmd))
            a_result = self.do_ssh(remote, "root", cmd)
            action_rc = a_result[2]
            self.message("ACTION: {} at {}: {} rc={}".format(action_name, remote, cmd, action_rc))
        return action_rc

    def do_ssh(self, remote_host, user, cmd):
        """
        ssh remote cmd exectution
        returns a tuple ( stdout-string, stderr, string, rc )
        """
        if remote_host:
            ssh_client = SSHClient()
            ssh_client.load_system_host_keys()
            ssh_client.connect(remote_host, username=user)
            (cmd_stdin, cmd_stdout, cmd_stderr) = ssh_client.exec_command(cmd)
            result_stdout = cmd_stdout.read().decode("utf8")
            result_stderr = cmd_stderr.read().decode("utf8")
            result_rc = cmd_stdout.channel.recv_exit_status()
            check_result = (result_stdout, result_stderr, result_rc)
            ssh_client.close()
        else:
            check_result=("", "", 20000)
        return check_result

if __name__ == "__main__":
    test01 = SaphanasrTest()
    while test01.count <= test01.repeat:
        test01.r_id = random.randrange(10000,99999,1)
        test01.read_saphana_sr()
        test01.topolo.update({'pSite': test01.search_in_area_for_object_by_key_value('Sites', 'srr', 'P')})
        test01.topolo.update({'sSite': test01.search_in_area_for_object_by_key_value('Sites', 'srr', 'S')})
        test01.topolo.update({'pHost': test01.search_in_area_for_object_by_key_value('Hosts', 'site', test01.topolo['pSite'])})
        test01.topolo.update({'sHost': test01.search_in_area_for_object_by_key_value('Hosts', 'site', test01.topolo['sSite'])})
        test01.message("TOPO: pSite={} sSite={} pHost={} sHost={}".format(test01.topolo['pSite'], test01.topolo['sSite'], test01.topolo['pHost'], test01.topolo['sHost']))
        test01.read_test_file()
        test_id = test01.test_data['test']
        if test01.repeat != 1:
            test01.message("TEST: {} testNr={} ######".format(test_id, test01.count))
        test01.test_rc = test01.process_test()
        if test01.test_rc == 0:
            test01.message("TEST: {} testNr={} PASSED successfully :) ######".format(test_id, test01.count))
        else:
            test01.message("TEST: {} testNr={} FAILED successfully ;) ######".format(test_id, test01.count))
        test01.count += 1
    if  test01.log_file_handle:
        test01.log_file_handle.close()
