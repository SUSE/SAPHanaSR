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

""" for ssh remote calls this module uses remoto """

from remoto.process import run
from remoto import connection
from remoto.process import check

class saphanasrtest:
    """
    class to check SAP HANA cluster during tests
    """

    def message(self,msg):
        """
        message with formatted timestamp
        """
        dateTime = time.strftime("%Y-%m-%d %H:%M:%S")
        print("{} {}".format(dateTime, msg))

    def __init__(self, *args):
        """
        constructor
        """
        self.message("INIT():")
        self.SR = {}
        self.testData = {}
        """ TODO: set testFile via cli-option (e.g. --testFile=xxx) """
        #self.testFile = "json/kpi.json"
        self.testFile = "-"
        """ old topology attributes """
        self.pSite = None
        self.sSite = None
        self.sHost = None
        self.pHost = None
        """ new topology attributes """
        self.topolo = { 'pSite': None, 'sSite': None, 'pHost': None, 'sHost': None }
        self.remoteNode = None
        parser = argparse.ArgumentParser()
        parser.add_argument("--testFile", help="specify the test file")
        parser.add_argument("--remoteNode", help="cluster node to use for ssh connection")
        parser.add_argument("--simulate", help="only simulate, dont call actions", action="store_true")
        args = parser.parse_args()
        if args.testFile:
            print("testFile: {}".format(args.testFile))
            self.testFile = args.testFile
        if args.remoteNode:
            print("remoteNode: {}".format(args.remoteNode))
            self.remoteNode = args.remoteNode

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
        """ TODO: use the 'real' program - maybe fallback to helpSAPHanaSR-showAttr for local testing """
        #cmd = [ './helpSAPHanaSR-showAttr', '--format=script'  ]
        cmd = [ 'ssh', self.remoteNode, 'SAPHanaSR-showAttr', '--format=script'  ]
        self.SR={}
        # self.message("CALL(): {}".format(cmd))
        result = subprocess.run(cmd, stdout=subprocess.PIPE)
        resultStr = result.stdout.decode()

        #print(type(result.stdout))
        #print((result.stdout))
        for line in resultStr.splitlines():
            #print("PRE SR: {}".format(self.SR))
            # <area>/<object>/<key-value>
            mo = re.search("(.*)/(.*)/(.*)", line)
            area = mo.group(1)
            objectName = mo.group(2)
            kV = mo.group(3)
            # <key>="<value>"
            mo = re.search("(.*)=\"(.*)\"", kV)
            key = mo.group(1)
            val = mo.group(2)
            # print("area='{}' object='{}' kV='{}' key='{}' val='{}'\n".format(area, objectName, kV, key, val))
            lObj=self.getObject(area, objectName)
            #lObj=None
            if lObj:
                # print("ADDTO lObj: {}".format(lObj))
                self.insertToObject(lObj,key,val)
                # print("ADDED: {}".format(self.getObject(area, objectName)))
            else:
                lObj = self.createObject(objectName, key, val)
                # print("CREATE lObj: {}".format(lObj))
                self.insertToArea(area, lObj)
            # print("POST SR: {}".format(self.SR))
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
                        #print("DBG: area={} k={} key={} valueSearch={} valueFound={}".format(areaName, k, key, value, lObj[key]))
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
            # print("check: {}".format(c))
            if areaName in lSR:
                lArea = lSR[areaName]
                if objectName in lArea:
                    lObj = lArea[objectName]
                    #print("DBG: lObj: {}".format(lObj))
                    if cKey in lObj:
                        lVal = lObj[cKey]
                        if re.search(cRegExp, lVal):
                            #self.message("MATCH: {}={} matched {}={}".format(cKey, lVal, cKey, cRegExp))
                            if checkResult <0:
                                checkResult = 0
                        else:
                            #self.message("NO-MATCH: {}={} does not match {}={}".format(cKey, lVal, cKey, cRegExp))
                            if checkResult <1:
                                checkResult = 1
                    else:
                        #self.message("MISSING: entry {} missing in SR".format(cKey))
                        if checkResult <2:
                            checkResult = 2
                else:
                    #self.message("MISSING: object {} missing in SR".format(objectName))
                    if checkResult <2:
                        checkResult = 2
            else:
                #self.message("MISSING: area {} missing in SR".format(areaName))
                if checkResult <2:
                    checkResult = 2
            #print("DBG: checkResult={}".format(checkResult))
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
            print("loop: {}".format(loops))
            processResult = -1
            self.readSAPHanaSR()
            """ TODO: alternative store checks in self.checks['pSite'] ( 'pSite', 'sSite', ...) to allow to move that redundant code to a method """
            """
            if 'pSite' in step:
                stepPSite = step['pSite']
                rcPsite = self.runChecks(stepPSite, 'Sites', self.pSite )
                if processResult < rcPsite:
                    processResult = rcPsite
            if 'sSite' in step:
                stepSsite = step['sSite']
                rcSsite = self.runChecks(stepSsite, 'Sites', self.sSite )
                if processResult < rcSsite:
                    processResult = rcSsite
            """
            
            """ TODO add also pHost and sHost """
            if 'pSite' in step:
                checks = step['pSite']
                #print("checks: {}".format(checks))
                topolo = self.topolo
                #print("topolo: {}".format(topolo))
                if 'pSite' in topolo:
                    site = topolo['pSite']
                    rcChecks = self.runChecks(checks, 'Sites', site)
                    if processResult < rcChecks:
                        processResult = rcChecks
            if 'sSite' in step:
                checks = step['sSite']
                #print("checks: {}".format(checks))
                topolo = self.topolo
                #print("topolo: {}".format(topolo))
                if 'sSite' in topolo:
                    site = topolo['sSite']
                    rcChecks = self.runChecks(checks, 'Sites', site)
                    if processResult < rcChecks:
                        processResult = rcChecks
            if 'pHost' in step:
                checks = step['pHost']
                #print("checks: {}".format(checks))
                topolo = self.topolo
                #print("topolo: {}".format(topolo))
                if 'pHost' in topolo:
                    host = topolo['pHost']
                    rcChecks = self.runChecks(checks, 'Hosts', host)
                    if processResult < rcChecks:
                        processResult = rcChecks
            if 'sHost' in step:
                checks = step['sHost']
                #print("checks: {}".format(checks))
                topolo = self.topolo
                #print("topolo: {}".format(topolo))
                if 'sHost' in topolo:
                    host = topolo['sHost']
                    rcChecks = self.runChecks(checks, 'Hosts', host)
                    if processResult < rcChecks:
                        processResult = rcChecks

            loops = loops + 1
            if processResult == 0:
                self.action(stepAction)
                break
            else:
                time.sleep(wait)
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
        self.message("PROC: testID={} testName={} testStart={}".format(testID, testName, testStart))
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
        aRc = 1
        if actionName == "":
            aRc = 0
        elif actionName == "ksi":
            remote = self.sHost
            self.message("ACTION: {} at {}".format(actionName, remote))
            """ TODO: get sidadm from testData """
            aRc = self.doSSH(self.sHost, ['su', '-', 'ha1adm', 'HDB', 'kill-9'])
        elif actionName == "kpi":
            kpi = 1
        elif actionName == "ssn":
            ssn = 1
        elif actionName == "spn":
            spn = 1
        elif actionName == "cleanup":
            remote = self.remoteNode
            self.message("ACTION: {} at {}".format(actionName, remote))
            """ TODO: get resource name from testData """
            aRc = self.doSSH(self.sHost, ['crm', 'resource', 'cleanup', 'ms_SAPHanaCon_HA1_HDB00'])
        if aRc != 0:
            self.message("ACTFAIL: action {} at {} rc={}".format(actionName, remote, aRc))

    def doSSH(self, remoteHost, cmdArray):
        """ ssh remote cmd exectution """
        if remoteHost:
            Connection = connection.get('ssh')
            remConn = Connection(remoteHost)
            checkResult=check(remConn, cmdArray)
            rc = checkResult[2]
        else:
            rc = 20000
        return rc

if __name__ == "__main__":
    test01 = saphanasrtest()
    test01.readSAPHanaSR()
    """ old style checks """
    test01.pSite = test01.searchInAreaForObjectByKeyValue('Sites', 'srr', 'P')
    test01.sSite = test01.searchInAreaForObjectByKeyValue('Sites', 'srr', 'S')
    test01.pHost = test01.searchInAreaForObjectByKeyValue('Hosts', 'site', test01.pSite)
    test01.sHost = test01.searchInAreaForObjectByKeyValue('Hosts', 'site', test01.sSite)
    """ new style checks """
    test01.topolo = {  'pSite': test01.searchInAreaForObjectByKeyValue('Sites', 'srr', 'P'),
                       'sSite': test01.searchInAreaForObjectByKeyValue('Sites', 'srr', 'S'),
                       'pHost': test01.searchInAreaForObjectByKeyValue('Hosts', 'site', test01.pSite),
                       'sHost': test01.searchInAreaForObjectByKeyValue('Hosts', 'site', test01.sSite)
    }
    print(test01.topolo)
    test01.message("TOPO(): pSite={} sSite={} pHost={} sHost={}".format(test01.pSite, test01.sSite, test01.pHost, test01.sHost))
    #test01.prettyPrint(test01.SR,0)
    test01.readTestFile()
    # print("test: {}".format(test01.testData))
    test01.processTest()
