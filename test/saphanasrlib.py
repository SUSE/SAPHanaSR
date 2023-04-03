# pylint: disable=consider-using-f-string
# pylint: disable=C0301
"""
 saphanasrtest.py
 Author:       Fabian Herschel, Mar 2023
 License:      GNU General Public License (GPL)
 Copyright:    (c) 2023 SUSE LLC
"""

import time
import subprocess
import re
import sys, json
import argparse
import random

# for ssh remote calls this module uses paramiko
from paramiko import SSHClient

class saphanasrtest:
    """
    class to check SAP HANA cluster during tests
    """
    version = "0.1.20230403.1448-lint04"

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
        except:
            print("{0} {1:<9s} {2}".format(date_time, "ERROR:", "Could not write log log file"))

    def message_fh(self, msg, file_handle):
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
        self.dict_sr = {}
        self.test_data = {}
        self.test_file = "-"
        self.default_checks_file = None
        self.properties_file = "properties.json"
        self.log_file = ""
        self.repeat = 1
        self.dump_failures = False
        self.topolo = { 'pSite': None, 'sSite': None, 'pHost': None, 'sHost': None }
        self.remote_node = None
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
            self.test_file = args.testFile
        if args.defaultChecksFile:
            self.message("PARAM: defaultChecksFile: {}".format(args.defaultChecksFile))
            self.default_checks_file = args.defaultChecksFile
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

    def insertToArea(self, area, object):
        """ insert an object dictionary to an area dictionary """
        l_sr = self.dict_sr.copy()
        if area in l_sr:
            l_dic = l_sr[area].copy()
            l_dic.update(object)
            l_sr[area].update(l_dic)
        else:
            l_dic = { area: object }
            l_sr.update(l_dic)
        self.dict_sr = l_sr.copy()

    def getObject(self, area, object_name):
        """ get an object dictionary inside the area dictionary """
        l_sr = self.dict_sr.copy()
        if area in l_sr:
            if object_name in l_sr[area]:
                return l_sr[area][object_name]
            else:
                return None
        else:
            return None

    def createObject(self, object_name, key, val):
        """ create a key: value dictionary for object object_name """
        l_obj = { object_name: { key: val } }
        return l_obj

    def insertToObject(self, object, key, value):
        """ insert a key-value pair into the object dictionary """
        l_obj = object
        l_dic = { key: value }
        l_obj.update(l_dic)
        return l_obj

    def readSAPHanaSR(self):
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
                l_obj=self.getObject(area, object_name)
                if l_obj:
                    self.insertToObject(l_obj,key,val)
                else:
                    l_obj = self.createObject(object_name, key, val)
                    self.insertToArea(area, l_obj)
        return 0

    def searchInAreaForObjectByKeyValue(self, area_name, key, value):
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

    def readTestFile(self):
        """ read Test Description, optionally defaultchecks and properties """
        if self.properties_file:
            prop_fh = open(self.properties_file, encoding="utf-8")
            self.test_data.update(json.load(prop_fh))
            prop_fh.close()
        if self.default_checks_file:
            dc_fh = open(self.default_checks_file, encoding="utf-8")
            self.test_data.update(json.load(dc_fh))
            dc_fh.close()
        if self.test_file == "-":
            self.test_data.update(json.load(sys.stdin))
        else:
            tf_fh = open(self.test_file, encoding="utf-8")
            self.test_data.update(json.load(tf_fh))
            tf_fh.close()
        self.message_fh("DEBUG: test_data: {}".format(str(self.test_data)),self.log_file_handle)

    def run_checks(self, checks, area_name, object_name ):
        """ run all checks for area and object """
        l_sr = self.dict_sr
        checkResult = -1
        failed_checks = ""
        for c in checks:
            # match <key>=<regExp>
            match_obj = re.search("(.*)(=)(.*)",c)
            c_key = match_obj.group(1)
            c_comp = match_obj.group(2)
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
                            if checkResult <0:
                                checkResult = 0
                        else:
                            if failed_checks == "":
                                failed_checks = "{}={}: {}={} !~ {}".format(area_name,object_name,c_key,l_val,c_reg_exp)
                            else:
                                failed_checks += "; {}={} !~ {}".format(c_key,l_val,c_reg_exp)
                            if checkResult <1:
                                checkResult = 1
            if (found == 0) and (checkResult < 2 ):
                checkResult = 2
        if self.dump_failures and failed_checks != "":
            self.message_fh("FAILED: {}".format(failed_checks), self.log_file_handle)
        return checkResult

    def process_topology_object(self, step, topology_object_name, area_name):
        rc_checks = -1
        if topology_object_name in step:
            checks = step[topology_object_name]
            if type(checks) is str: 
                check_ptr = checks
                self.message_fh("DEBUG: check_ptr {}".format(check_ptr), self.log_file_handle)
                checks = self.test_data["checkPtr"][check_ptr]
                #for c in checks:
                #    self.message("DEBUG: check_ptr {} check {}".format(check_ptr,c))
            topolo = self.topolo
            if topology_object_name in topolo:
                object_name = topolo[topology_object_name]
                rc_checks = self.run_checks(checks, area_name, object_name)
        return(rc_checks)

    def processStep(self, step):
        """ process a single step including optional loops """
        stepID = step['step']
        stepName = step['name']
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
        self.message("PROC: stepID={} stepName='{}' step_next={} step_action='{}'".format(stepID, stepName, step_next, step_action))
        while loops < max_loops:
            loops = loops + 1
            if self.dump_failures == False:
                print(".", end='', flush=True)
            processResult = -1
            self.readSAPHanaSR()
            processResult = max ( self.process_topology_object(step, 'pSite', 'Sites'),
                                  self.process_topology_object(step, 'sSite', 'Sites'),
                                  self.process_topology_object(step, 'pHost', 'Hosts'),
                                  self.process_topology_object(step, 'sHost', 'Hosts'))
            if processResult == 0:
                break
            else:
                time.sleep(wait)
        if self.dump_failures == False:
            print("")
        self.message("STATUS: step {} checked in {} loop(s)".format(stepID, loops))
        if processResult == 0:
            aRc = self.action(step_action)
        return processResult

    def processSteps(self):
        """ process a seria of steps till next-step is "END" or there is no next-step """
        testStart = self.test_data['start']
        step=self.getStep(testStart)
        stepStep = step['step']
        rc = 0
        """ onfail for first step is 'break' """
        onfail = 'break' 
        while stepStep != "END":
            step_next = step['next']
            processResult = self.processStep(step)
            if processResult == 0:
                self.message("STATUS: Test step {} passed successfully".format(stepStep))
            else:
                rc = 1
                self.message("STATUS: Test step {} FAILED successfully ;-)".format(stepStep))
                """ TODO: add onfail handling (cuurently only brak for furst step and continue for others) """
                if onfail == 'break':
                    break
            step=self.getStep(step_next)
            if step:
                stepStep = step['step']
            else:
                """ check, why we run into this code path """
                break
            """ onfail for all next steps is 'continue' to run also the recovery steps """
            onfail = 'continue'
        return(rc)

    def processTest(self):
        """ process the entire test defined in test_data """
        testID = self.test_data['test']
        testName = self.test_data['name']
        testStart = self.test_data['start']
        testSID = self.test_data['sid']
        testResource = self.test_data['mstResource']
        self.message("PROC: testID={} testName={} testStart={} testSID={}".format(testID, testName, testStart, testSID, testResource))
        rc = self.processSteps()
        return(rc)

    def getStep(self, stepName):
        """ query for a given step with stepName in test_data """
        step = None
        for s in self.test_data['steps']:
            if s['step'] == stepName:
                step = s
                break
        return step

    def action(self, actionName):
        """ perform a given action """
        remote = self.remote_node
        cmd = ""
        aRc = 1
        # resource = "ms_SAPHanaCon_HA1_HDB00"
        testSID = self.test_data['sid']
        resource = self.test_data['mstResource']
        actionArr = actionName.split(" ")
        actionNameShort = actionArr[0]
        if actionName == "":
            aRc = 0
        elif actionName == "ksi":
            remote = self.topolo['sHost']
            cmd = "su - {}adm HDB kill-9".format(testSID.lower())
        elif actionName == "kpi":
            remote = self.topolo['pHost']
            cmd = "su - {}adm HDB kill-9".format(testSID.lower())
        elif actionName == "kpx":
            remote = self.topolo['pHost']
            cmd = "pkill -f -u {}adm --signal 11 hdbindexserver".format(testSID.lower())
        elif actionName == "ksx":
            remote = self.topolo['sHost']
            cmd = "pkill -f -u {}adm --signal 11 hdbindexserver".format(testSID.lower())
        elif actionName == "bmt":
            remote = self.topolo['sHost']
            cmd = "su - {}adm -c 'hdbnsutil -sr_takeover'".format(testSID.lower())
        elif actionName == "ssn":
            remote = self.remote_node
            cmd = "crm node standby {}".format(self.topolo['sHost'])
        elif actionName == "osn":
            remote = self.remote_node
            cmd = "crm node online {}".format(self.topolo['sHost'])
        elif actionName == "spn":
            remote = self.remote_node
            cmd = "crm node standby {}".format(self.topolo['pHost'])
        elif actionName == "opn":
            remote = self.remote_node
            cmd = "crm node online {}".format(self.topolo['pHost'])
        elif actionName == "cleanup":
            """ TODO: get resource name from test_data """
            remote = self.remote_node
            cmd = "crm resource cleanup {}".format(resource)
        elif actionNameShort == "sleep":
            remote = self.remote_node
            if len(actionArr) == 2:
                actionParameter = actionArr[1]
            else:
                actionParameter = "60"
            cmd = "sleep {}".format(actionParameter)
        elif actionNameShort == "shell":
            remote = 'localhost'
            actionParameter = " ".join(actionArr[1:])
            cmd = "bash {}".format(actionParameter)
        if cmd != "":
            self.message("ACTION: {} at {}: {}".format(actionName, remote, cmd))
            aResult = self.do_ssh(remote, "root", cmd)
            aRc = aResult[2]
            self.message("ACTION: {} at {}: {} rc={}".format(actionName, remote, cmd, aRc))
        return(aRc)

    def do_ssh(self, remote_host, user, cmd):
        """
        ssh remote cmd exectution
        returns a tuple ( stdout-string, stderr, string, rc )
        """
        if remote_host:
            ssh_client = SSHClient()
            ssh_client.load_system_host_keys()
            ssh_client.connect(remote_host, username=user)
            (cmdStdin, cmdStdout, cmdStderr) = ssh_client.exec_command(cmd)
            resultStdout = cmdStdout.read().decode("utf8")
            resultStderr = cmdStderr.read().decode("utf8")
            resultRc = cmdStdout.channel.recv_exit_status()
            checkResult = (resultStdout, resultStderr, resultRc)
            ssh_client.close()
        else:
            checkResult=("", "", 20000)
        return(checkResult)

if __name__ == "__main__":
    test01 = saphanasrtest()
    test01.count = 1
    while test01.count <= test01.repeat:
        test01.r_id = random.randrange(10000,99999,1)
        test01.readSAPHanaSR()
        test01.topolo.update({'pSite': test01.searchInAreaForObjectByKeyValue('Sites', 'srr', 'P')})
        test01.topolo.update({'sSite': test01.searchInAreaForObjectByKeyValue('Sites', 'srr', 'S')})
        test01.topolo.update({'pHost': test01.searchInAreaForObjectByKeyValue('Hosts', 'site', test01.topolo['pSite'])})
        test01.topolo.update({'sHost': test01.searchInAreaForObjectByKeyValue('Hosts', 'site', test01.topolo['sSite'])})
        test01.message("TOPO: pSite={} sSite={} pHost={} sHost={}".format(test01.topolo['pSite'], test01.topolo['sSite'], test01.topolo['pHost'], test01.topolo['sHost']))
        test01.readTestFile()
        testID = test01.test_data['test']
        if test01.repeat != 1:
            test01.message("TEST: {} testNr={} ######".format(testID, test01.count))
        rc = test01.processTest()
        if rc == 0:
            test01.message("TEST: {} testNr={} PASSED successfully :) ######".format(testID, test01.count)) 
        else:
            test01.message("TEST: {} testNr={} FAILED successfully ;) ######".format(testID, test01.count)) 
        test01.count += 1
    if  test01.log_file_handle:
        test01.log_file_handle.close()
