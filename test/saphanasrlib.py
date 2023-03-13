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

""" for ssh remote calls this module uses paramiko """
from paramiko import SSHClient

class saphanasrtest:
    """
    class to check SAP HANA cluster during tests
    """
    version = "0.1.20230313.1257"

    def message(self,msg):
        """
        message with formatted timestamp
        """
        """ TODO: field-with for first word (like TEST:, ACTION: and others) """
        """ TODO: specify, if message should be written to stdout, stderr and/or log file """
        dateTime = time.strftime("%Y-%m-%d %H:%M:%S")
        msgArr = msg.split(" ")
        print("{0} {1:<9s} {2}".format(dateTime, msgArr[0], " ".join(msgArr[1:])))

    def __init__(self, *args):
        """
        constructor
        """
        self.message("INIT(): {}".format(self.version))
        self.SR = {}
        self.testData = {}
        self.testFile = "-"
        self.repeat = 1
        self.topolo = { 'pSite': None, 'sSite': None, 'pHost': None, 'sHost': None }
        self.remoteNode = None
        parser = argparse.ArgumentParser()
        parser.add_argument("--testFile", help="specify the test file")
        parser.add_argument("--remoteNode", help="cluster node to use for ssh connection")
        parser.add_argument("--simulate", help="only simulate, dont call actions", action="store_true")
        parser.add_argument("--repeat", help="how often to repeat the test")
        args = parser.parse_args()
        if args.testFile:
            self.message("PARAM: testFile: {}".format(args.testFile))
            self.testFile = args.testFile
        if args.remoteNode:
            self.message("PARAM: remoteNode: {}".format(args.remoteNode))
            self.remoteNode = args.remoteNode
        if args.repeat:
            self.message("PARAM: repeat: {}".format(args.repeat))
            self.repeat = int(args.repeat)

    def insertToArea(self, area, object):
        """ insert an object dictionary to an area dictionary """
        lSR = self.SR.copy()
        if area in lSR:
            lDic = lSR[area].copy()
            lDic.update(object)
            lSR[area].update(lDic)
        else:
            lDic = { area: object }
            lSR.update(lDic)
        self.SR = lSR.copy()

    def getObject(self, area, objectName):
        """ get an onject dictionary inside the area dictionary """
        lSR = self.SR.copy()
        if area in lSR:
            if objectName in lSR[area]:
                return lSR[area][objectName]
            else:
                return None
        else:
            return None

    def createObject(self, objectName, key, val):
        """ create a key: value dictionary for object objectName """
        lObj = { objectName: { key: val } }
        return lObj

    def insertToObject(self, object, key, value):
        """ insert a key-value pair into the object dictionary """
        lObj = object
        lDic = { key: value }
        lObj.update(lDic)
        return lObj

    def readSAPHanaSR(self):
        """ method to read SAPHanaSR-showAttr cluster attributes and create a nested dictionary structure representing the data """
        #cmd = [ './helpSAPHanaSR-showAttr', '--format=script'  ]
        cmd = "SAPHanaSR-showAttr --format=script"
        self.SR={}
        resultSR = self.doSSH(self.remoteNode, "root", cmd)
        for line in resultSR[0].splitlines():
            """ match and split: <area>/<object>/<key-value> """
            mo = re.search("(.*)/(.*)/(.*)", line)
            area = mo.group(1)
            objectName = mo.group(2)
            kV = mo.group(3)
            """ match and split <key>="<value>" """
            mo = re.search("(.*)=\"(.*)\"", kV)
            key = mo.group(1)
            val = mo.group(2)
            lObj=self.getObject(area, objectName)
            if lObj:
                self.insertToObject(lObj,key,val)
            else:
                lObj = self.createObject(objectName, key, val)
                self.insertToArea(area, lObj)
        return 0

    def searchInAreaForObjectByKeyValue(self, areaName, key, value):
        """ method to search in SR for an ObjectName filtered by 'area' and key=value """
        objectName = None
        lSR = self.SR
        if areaName in lSR:
            lArea = lSR[areaName]
            for k in lArea.keys():
                lObj = lArea[k]
                if key in lObj:
                    if lObj[key] == value:
                        objectName = k
                        """ currently we only return the first match """
                        break
        return objectName

    def prettyPrint(self, dictionary,level):
        """ debug method for nested dictionary """
        print("{")
        count = 0
        for k in dictionary.keys():
            if count > 0:
                print(",")
            if isinstance(dictionary[k],dict):
                print("'{}': ".format(k))
                self.prettyPrint(dictionary[k], level+1)
            else:
                print("'{}': '{}'".format(k,dictionary[k]))
            count = count + 1
        print("}")

    def readTestFile(self):
        """ TODO: read from file rather from stdin """
        if self.testFile == "-":
            self.testData = json.load(sys.stdin)
        else:
            f = open(self.testFile)
            self.testData = json.load(f)

    def runChecks(self, checks, areaName, objectName ):
        """ run all checks for area and object """
        lSR = self.SR
        checkResult = -1
        for c in checks:
            """ match <key>=<regExp> """
            mo = re.search("(.*)(=)(.*)",c)
            cKey = mo.group(1)
            cComp = mo.group(2)
            cRegExp = mo.group(3)
            found = 0
            if areaName in lSR:
                lArea = lSR[areaName]
                if objectName in lArea:
                    lObj = lArea[objectName]
                    if cKey in lObj:
                        lVal = lObj[cKey]
                        found = 1
                        if re.search(cRegExp, lVal):
                            if checkResult <0:
                                checkResult = 0
                        else:
                            if checkResult <1:
                                checkResult = 1
            if (found == 0) and (checkResult < 2 ):
                checkResult = 2
        return checkResult

    def processStep(self, step):
        """ process a single step including otional loops """
        stepID = step['step']
        stepName = step['name']
        stepNext = step['next']
        if 'loop' in step:
            maxLoops = step['loop']
        else:
            maxLoops = 1
        if 'wait' in step:
            wait = step['wait']
        else:
            wait = 2
        loops = 0
        if 'post' in step:
            stepAction = step['post']
        else:
            stepAction = ""
        self.message("PROC: stepID={} stepName='{}' stepNext={} stepAction={}".format(stepID, stepName, stepNext, stepAction))
        while loops <= maxLoops:
            print(".", end='', flush=True)
            processResult = -1
            self.readSAPHanaSR()
            if 'pSite' in step:
                checks = step['pSite']
                topolo = self.topolo
                if 'pSite' in topolo:
                    site = topolo['pSite']
                    rcChecks = self.runChecks(checks, 'Sites', site)
                    if processResult < rcChecks:
                        processResult = rcChecks
            if 'sSite' in step:
                checks = step['sSite']
                topolo = self.topolo
                if 'sSite' in topolo:
                    site = topolo['sSite']
                    rcChecks = self.runChecks(checks, 'Sites', site)
                    if processResult < rcChecks:
                        processResult = rcChecks
            if 'pHost' in step:
                checks = step['pHost']
                topolo = self.topolo
                if 'pHost' in topolo:
                    host = topolo['pHost']
                    rcChecks = self.runChecks(checks, 'Hosts', host)
                    if processResult < rcChecks:
                        processResult = rcChecks
            if 'sHost' in step:
                checks = step['sHost']
                topolo = self.topolo
                if 'sHost' in topolo:
                    host = topolo['sHost']
                    rcChecks = self.runChecks(checks, 'Hosts', host)
                    if processResult < rcChecks:
                        processResult = rcChecks

            loops = loops + 1
            if processResult == 0:
                break
            else:
                time.sleep(wait)
        print("")
        self.message("STATUS: step {} checked in {} loops)".format(stepID, loops))
        if processResult == 0:
            aRc = self.action(stepAction)
        return processResult

    def processSteps(self):
        """ process a seria of steps till next-step is "END" or there is no next-step """
        testStart = self.testData['start']
        step=self.getStep(testStart)
        stepStep = step['step']
        while stepStep != "END":
            stepNext = step['next']
            processResult = self.processStep(step)
            if processResult == 0:
                self.message("STATUS: Test step {} passed successfully".format(stepStep))
            else:
                self.message("STATUS: Test step {} FAILED successfully ;-)".format(stepStep))
                """ TODO: add onfail handling """
                break
            step=self.getStep(stepNext)
            if step:
                stepStep = step['step']
            else:
                """ check, why we run into this code path """
                break

    def processTest(self):
        """ process the entire test defined in testData """
        testID = self.testData['test']
        testName = self.testData['name']
        testStart = self.testData['start']
        testSID = self.testData['sid']
        testResource = self.testData['mstResource']
        self.message("PROC: testID={} testName={} testStart={} testSID={}".format(testID, testName, testStart, testSID, testResource))
        self.processSteps()

    def getStep(self, stepName):
        """ query for a given step with stepName in testData """
        step = None
        for s in self.testData['steps']:
            if s['step'] == stepName:
                step = s
                break
        return step

    def action(self, actionName):
        """ perform a given action """
        remote = self.remoteNode
        cmd = ""
        aRc = 1
        # resource = "ms_SAPHanaCon_HA1_HDB00"
        testSID = self.testData['sid']
        resource = self.testData['mstResource']
        if actionName == "":
            aRc = 0
        elif actionName == "ksi":
            """ TODO: get sidadm from testData """
            remote = self.topolo['sHost']
            cmd = "su - {}adm HDB kill-9".format(testSID.lower())
        elif actionName == "kpi":
            """ TODO: get sidadm from testData """
            remote = self.topolo['pHost']
            cmd = "su - {}adm HDB kill-9".format(testSID.lower())
        elif actionName == "ssn":
            remote = self.remoteNode
            cmd = "crm node standby {}".format(self.topolo['sHost'])
        elif actionName == "osn":
            remote = self.remoteNode
            cmd = "crm node online {}".format(self.topolo['sHost'])
        elif actionName == "spn":
            remote = self.remoteNode
            cmd = "crm node standby {}".format(self.topolo['pHost'])
        elif actionName == "opn":
            remote = self.remoteNode
            cmd = "crm node online {}".format(self.topolo['pHost'])
        elif actionName == "cleanup":
            """ TODO: get resource name from testData """
            remote = self.remoteNode
            cmd = "crm resource cleanup {}".format(resource)
        elif actionName == "sleep":
            """ TODO: get sleep time from testData """
            remote = self.remoteNode
            cmd = "sleep 60"
        if cmd != "":
            self.message("ACTION: {} at {}: {}".format(actionName, remote, cmd))
            aResult = self.doSSH(remote, "root", cmd)
            aRc = aResult[2]
            self.message("ACTION: {} at {}: {} rc={}".format(actionName, remote, cmd, aRc))
        return(aRc)

    def doSSH(self, remoteHost, user, cmd):
        """ 
        ssh remote cmd exectution 
        returns a tuple ( stdout-string, stderr, string, rc )
        """
        if remoteHost:
            sshCl = SSHClient() 
            sshCl.load_system_host_keys()
            sshCl.connect(remoteHost, username=user)
            (cmdStdin, cmdStdout, cmdStderr) = sshCl.exec_command(cmd)
            resultStdout = cmdStdout.read().decode("utf8")
            resultStderr = cmdStderr.read().decode("utf8")
            resultRc = cmdStdout.channel.recv_exit_status()
            checkResult = (resultStdout, resultStderr, resultRc)
            sshCl.close()
        else:
            checkResult=("", "", 20000)
        return(checkResult)

if __name__ == "__main__":
    test01 = saphanasrtest()
    test01.count = 1
    while test01.count <= test01.repeat:
        test01.readSAPHanaSR()
        test01.topolo.update({'pSite': test01.searchInAreaForObjectByKeyValue('Sites', 'srr', 'P')})
        test01.topolo.update({'sSite': test01.searchInAreaForObjectByKeyValue('Sites', 'srr', 'S')})
        test01.topolo.update({'pHost': test01.searchInAreaForObjectByKeyValue('Hosts', 'site', test01.topolo['pSite'])})
        test01.topolo.update({'sHost': test01.searchInAreaForObjectByKeyValue('Hosts', 'site', test01.topolo['sSite'])})
        test01.message("TOPO(): pSite={} sSite={} pHost={} sHost={}".format(test01.topolo['pSite'], test01.topolo['sSite'], test01.topolo['pHost'], test01.topolo['sHost']))
        test01.readTestFile()
        if test01.repeat != 1:
            testID = test01.testData['test']
            test01.message("TEST: {} testNr={} ######".format(testID, test01.count))
        test01.processTest()
        test01.count += 1
