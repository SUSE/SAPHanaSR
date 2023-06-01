#!/usr/bin/python3
# pylint: disable=consider-using-f-string
# pylint: disable=fixme
"""
 saphana_sr_tools.py
 Author:       Fabian Herschel, May 2023
 License:      GNU General Public License (GPL)
 Copyright:    (c) 2023 SUSE LLC

# TODO: STEP01: SID-autodetection - get SID from query for SAPHanaController/SAPHanaTopologyResource - warn, if there are no or more than one SIDs found.
# TODO: STEP02: Think also about multi SID implementation - maybe by using multiple HanaCluster objects (one per SID)
"""

import argparse
import json
import os
import re
import sys
import subprocess
import xml.etree.ElementTree as ET

def get_sort_value(item, index, **kargs):
    """ get_value(item, index, **kargs)
        item is the single entity item to be sorted
        index is the 'field' in item to sort-by
        with type='int' or type='str' you could define the replace value for non-existing dictionary entries in item
    """
    if index in item:
        return item[index]
    if 'type' in kargs:
        if kargs['type'] == 'int':
            return 0
        elif kargs['type'] == 'str':
            return ''
    return  None

def shorten(column_name):
    """ shortens column name
        e.g. (1) hana_ha1_site -> site              ( a node attribute)
             (2) hana_ha1_site_mns_S1 -> mns        ( a site attribute )
             (3) hana_ha1_global_topology -> global ( a global attribute )
    """
    match_obj = re.search("hana_..._glob_(.*)",column_name)    # (3)
    if match_obj != None:
        column_name = match_obj.group(1)
    match_obj = re.search("hana_..._site_(.*)_",column_name)   # (2)
    if match_obj != None:
        column_name = match_obj.group(1)
    match_obj = re.search("hana_..._(.*)",column_name)         # (1)
    if match_obj != None:
        column_name = match_obj.group(1)
    return column_name

class HanaCluster():

    global selections 
    selections = {
                    'all': {
                                    'global'   : ['.*'],
                                    'resource' : ['.*'],
                                    'site'     : ['.*'],
                                    'host'     : ['.*'],
                               },
                    'default': {
                                    'global'   : ['Global', 'cib-time', 'maintenance', 'prim', 'sec', 'sid', 'topology'],
                                    'resource' : ['Resource', 'maintenance', 'is_managed', 'promotable'],
                                    'site'     : ['Site', 'lpt', 'lss', 'mns', 'opMode', 'srHook', 'srMode', 'srPoll', 'srr'],
                                    'host'     : ['Host', 'clone_state', 'node_state', 'roles', 'score', 'site', 'sra', 'srah', 'standby', 'version', 'vhost'],
                               },
                    'sr': {
                                    'global'   : ['Global', 'cib-time', 'maintenance', 'prim', 'sec', 'sid', 'topology'],
                                    'resource' : ['Resource', 'maintenance', 'is_managed', 'promotable'],
                                    'site'     : ['Site', 'lpt', 'lss', 'mns', 'opMode', 'srHook', 'srMode', 'srPoll', 'srr'],
                                    'host'     : ['Host', 'clone_state', 'roles', 'score', 'site', 'sra', 'srah', 'vhost'],
                                 },
                    'minimal': {
                                    'global'   : ['Global', 'cib-time', 'maintenance', 'prim', 'sec', 'sid', 'topology'],
                                    'resource' : ['Resource', 'maintenance', 'is_managed'],
                                    'site'     : ['Site', 'lpt', 'lss', 'mns', 'srHook', 'srPoll', 'srr'],
                                    'host'     : ['Host', 'clone_state', 'roles', 'score', 'site'],
                                 },
                    'cluster': {
                                    'global'   : ['Global', 'cib-time', 'cluster-name', 'have-quorum', 'maintenance', 'sid', 'stonith-enabled', 'stonith-timeout', 'stonith-watchdog-timeout', 'topology'],
                                    'resource' : ['Resource', 'maintenance', 'is_managed', 'promotable'],
                                    'site'     : ['Site', 'lpt', 'lss', 'mns', 'opMode', 'srHook', 'srMode', 'srPoll', 'srr'],
                                    'host'     : ['Host', 'clone_state', 'node_state', 'roles', 'score', 'site', 'sra', 'srah', 'standby', 'vhost'],
                               },
                    'cluster2': {
                                    'global'   : ['Global', 'cib-time', 'cluster-name', 'have-quorum', 'maintenance', 'sid', 'stonith-enabled', 'stonith-timeout', 'stonith-watchdog-timeout', 'topology'],
                                    'resource' : ['Resource', 'maintenance', 'is_managed', 'promotable'],
                                    'site'     : ['Site', 'lpt', 'lss', 'mns', 'opMode', 'srHook', 'srMode', 'srPoll', 'srr'],
                                    'host'     : ['Host', 'clone_state', 'node_state', 'roles', 'score', 'site', 'sra', 'srah', 'standby', 'vhost', 'fail.*'],
                               },
                    'cluster3': {
                                    'global'   : ['-dc.*'],
                                    'resource' : ['Resource', 'maintenance', 'is_managed', 'promotable'],
                                    'site'     : ['Site', 'lpt', 'lss', 'mns', 'opMode', 'srHook', 'srMode', 'srPoll', 'srr'],
                                    'host'     : ['Host', 'clone_state', 'node_state', 'roles', 'score', 'site', 'sra', 'srah', 'standby', 'vhost', 'fail.*'],
                               },
                }

    def __init__(self):
        self.tree = None
        self.root = None
        self.glob_dict = None
        self.res_dict = None
        self.site_dict = None
        self.host_dict = None
        self.selection = 'test'
        self.config = {
            'cib_file': None,
            'format': "table",
            'select': "default",
            'sid': None, 
            'sort': None,
            'sort-reverse': False,
                      }
        self.sids = []

    def xml_import(self, filename):
        if filename == None:
            # use cibadmin as input
            cmd = "cibadmin -Ql"
            xml_string = subprocess.check_output(cmd.split(" "))
            self.root = ET.fromstring(xml_string)
        elif filename == "-":
            # read from stdin
            self.tree = ET.parse(sys.stdin)
            self.root = self.tree.getroot()
            pass
        else:
            # read from filename
            if os.path.isfile(filename):
                self.tree = ET.parse(filename)
                self.root = self.tree.getroot()
            else:
                print(f"cib file {filename} not found")
                sys.exit(2)

    def fill_glob_dict(self):
        """
        fill_glob_dict() - fill the 'global' dictionary
            global area is for attributes not assigned for a node/host, site nor resource
            typically this includes the cib-time, stonith-enabled and all hana_sid_glob_ attributes
        """
        self.glob_dict =  {"global": {} }
        global_glob_dict = self.glob_dict['global']
        if 'sid' in self.config and self.config['sid']:
            global_glob_dict.update({'sid': self.config['sid'].upper()})
        # handle all attributes from properties but not site attributes (hana_<sid>_site_<name>_<site>)
        for nv in self.root.findall("./configuration/crm_config/cluster_property_set/nvpair"):
            # TODO add only cluster and hana_xxx_global_nnnn attributes - for now we add all
            name = nv.attrib['name']
            value = nv.attrib["value"]
            if self.is_hana_attribute(name):
                if self.is_hana_glob_attribute(name):
                    sid = self.get_sid_from_attribute(name)
                    if sid == self.config['sid']:
                        global_glob_dict.update({shorten(name): value})
            else:
                global_glob_dict.update({name: value})
        # handle all cib attributes at top-level
        cib_attrs = self.root.attrib
        if 'cib-last-written' in cib_attrs:
            global_glob_dict.update({'cib-time': cib_attrs["cib-last-written"]})
        if 'have-quorum' in cib_attrs:
            global_glob_dict.update({'have-quorum': cib_attrs["have-quorum"]})

    def fill_res_dict(self):
        """
        fill_res_dict() - fill the 'resource' dictionary
        TODO: Controller and Topology part very similar -> create a method for processing that
        """
        sid = self.config["sid"].upper()
        self.res_dict = {}
        # Controller
        con_res_arr = self.root.findall(f"./configuration/resources//*[@type='SAPHanaController']/instance_attributes/nvpair[@name='SID'][@value='{sid}']/../../..")
        if len(con_res_arr) == 1:
            con_res = con_res_arr[0]
            con_name = con_res.attrib['id']
            self.res_dict.update({con_name: {}}) 
            res_res_dict = self.res_dict[con_name]
            for ma in con_res.findall("./meta_attributes/nvpair"):
                name = ma.attrib['name']
                value = ma.attrib["value"]
                res_res_dict.update({name: value})
        # Topology
        top_res_arr = self.root.findall(f"./configuration/resources//*[@type='SAPHanaTopology']/instance_attributes/nvpair[@name='SID'][@value='{sid}']/../../..")
        if len(top_res_arr) == 1:
            top_res = top_res_arr[0]
            top_name = top_res.attrib['id']
            self.res_dict.update({top_name: {}}) 
            res_res_dict = self.res_dict[top_name]
            for ma in top_res.findall("./meta_attributes/nvpair"):
                name = ma.attrib['name']
                value = ma.attrib["value"]
                res_res_dict.update({name: value})

    def fill_site_dict(self):
        """
        TODO: description
        hana_<sid>_site_<name>_<site>
        """
        self.site_dict = {}
        for nv in self.root.findall("./configuration/crm_config/cluster_property_set/nvpair"):
            name = nv.attrib['name']
            value = nv.attrib["value"]
            site = self.is_site_attribute(name, return_site_name=True)
            sid  = self.get_sid_from_attribute(name)
            if site  and sid == self.config['sid']:
                if not(site in self.site_dict):
                    self.site_dict.update({site: {}})
                site_site_dict = self.site_dict[site]
                # for sites we already use the shortened attribute name (site-part in the name sis also removed to match the same column later)
                site_site_dict.update({shorten(name): value})
            else:
                pass
 
    def fill_host_dict(self):
        """
        TODO: description
        """
        self.host_dict = {}
        for host_obj in self.root.findall("./configuration/nodes/*"):
            hostname = host_obj.attrib['uname']
            self.host_dict.update({hostname: {}})
            node_table = self.host_dict[hostname]
            self.fill_node(hostname, node_table)

    def fill_node(self, hostname, node_table):
        """
        TODO: description
        """
        host_obj = self.root.findall(f"./configuration/nodes/*[@uname='{hostname}']")[0]
        for nv in host_obj.findall("./instance_attributes/nvpair"):
            name = nv.attrib['name']
            value = nv.attrib["value"]
            if self.is_hana_attribute(name):
                sid = self.get_sid_from_attribute(name)
                if sid == self.config['sid']:
                    node_table.update({shorten(name): value})
            else:
                node_table.update({shorten(name): value})
        host_status_obj = self.root.findall(f"./status/node_state[@uname='{hostname}']")[0]
        for nv in host_status_obj.findall("./transient_attributes/instance_attributes/nvpair"):
            name = nv.attrib['name']
            value = nv.attrib["value"]
            if self.is_hana_attribute(name):
                sid = self.get_sid_from_attribute(name)
                if sid == self.config['sid']:
                    node_table.update({shorten(name): value})
            else:
                node_table.update({shorten(name): value})
        

    def is_site_attribute(self, column_name, **kargs):
        """
        TODO: description
        """
        return_site_name = False
        if 'return_site_name' in kargs:
            return_site_name = kargs['return_site_name']
        match_obj = re.search("hana_..._site_.*_(.*)",column_name)
        if match_obj:
            if return_site_name:
                return match_obj.group(1)
            else:
                return True
        else:
            if return_site_name:
                return None
        return False;

    def is_hana_attribute(self, name):
        """
        TODO: description
        """
        match_obj = re.match("hana_.*",name)
        if match_obj:
           return True
        return False

    def is_hana_glob_attribute(self, name):
        """
        TODO: description
        """
        match_obj = re.match("hana_..._glob_.*",name)
        if match_obj:
           return True
        return False

    def get_sid_from_attribute(self, name):
        """
        TODO: description
        """
        sid = None
        match_obj = re.match("hana_(...)_",name)
        if match_obj:
            sid = match_obj.group(1)
        return sid


    def print_dic_as_table(self, print_dic, area, table_name):
        """
        TODO: description
        TODO: break this method into smaller pieces
        """
        # TODO: option for bar-character (default "-")
        # TODO: option for empty line at end of table (default True) or like 'end' in print end='' is no-line end="bar" is same a after headline end="space" (default) is one empty line
        # build headline: 
        #  1. get all keys (column-names) used by any of the top-level-objects
        #  2. get the max length of each column (max(column_name, max(any column_value))
        column_names = []
        column_length = {}
        column_length[table_name] = len(table_name)
        for key in print_dic:
            element_keys = list(print_dic[key].keys())
            column_names.extend(element_keys)
            column_length[table_name] = max(column_length[table_name], len(key))
        column_names = sorted(list(dict.fromkeys(column_names)))
        column_names.insert(0, table_name)
        for col in column_names[1:]:
            col_len = len(shorten(col)) 
            for key in print_dic:
                if col in print_dic[key]:
                    col_len = max(col_len, len(print_dic[key][col]))
            column_length[col] = col_len
        #
        # print headline
        #
        bar_len = 0
        for col in column_names:                 
            if self.filter(area, col) == True:
                if col in column_length:
                    col_len = column_length[col]
                else:
                    col_len = 1
                print("{0:<{width}} ".format(shorten(col), width=col_len), end='')
                bar_len += col_len + 1
        print()
        print('-' * bar_len)
        #
        # print rows
        #
        for key in print_dic:
            for col in column_names[0:]:        
                if self.filter(area, col) == True:
                    if col in column_length:
                        col_len = column_length[col]
                    else:
                        col_len = 1
                    if col == table_name:
                        value = key
                    elif col in print_dic[key]:
                        value = print_dic[key][col]
                    else:
                        value = ""
                    print("{0:<{width}} ".format(value, width=col_len), end='')
            print()
        print()

    def print_dic_as_json(self, print_dic, table_name):
        """
        TODO: description
        """
        json_obj = json.dumps({table_name: print_dic}, indent = 4)
        print(json_obj)

    def print_all_as_json(self):
        """
        TODO: description
        """
        # TODO: maybe 'Global', 'Site', 'Host", ... configurable strings?
        json_obj = json.dumps( {
                                 'Global': self.glob_dict,
                                 'Resource': self.res_dict,
                                 'Site':   self.site_dict,
                                 'Host':   self.host_dict
                               }, indent = 4
                             )
        print(json_obj)

    def print_dic_as_path(self, print_dic, area, table_name, **kargs):
        """
        TODO: description
        """
        quote=''
        if 'quote' in kargs:
            quote = kargs['quote']
        for key in print_dic:
            for col in print_dic[key]:
                if self.filter(area, col) == True:
                    value = print_dic[key][col]
                    print(f"{table_name}/{key}/{col}={quote}{value}{quote}")
                
    def filter(self, area, column_name):
        ''' filter column_names 
            False, if column should be skipped
            True, if column should be printed
            TODO: filter sets might allow custom config via json file (filter set per area)
        '''
        select = self.config['select']
        if select in selections and area in selections[select]:
            the_selection = selections[select][area]
            after_loop = False
            for pat in the_selection:
                on_match = True
                if pat[0]=='-':
                    after_loop = True
                    on_match = False
                    pat = pat[1:]
                elif pat[0]=='+':
                    pat = pat[1:]
                match_obj = re.match(pat + '$',column_name)
                if match_obj:
                    return on_match
            return after_loop
        return True

    def get_sids(self):
        root = self.root
        sids = []
        for ia in root.findall("./configuration/resources//*[@type='SAPHanaController']/instance_attributes/nvpair[@name='SID']"):
            sids.append(ia.attrib['value'])
        self.sids = sids
    


if __name__ == "__main__":
    myCluster = HanaCluster()
    parser = argparse.ArgumentParser()
    parser.add_argument("--cib", help="specify the cibfile file")
    parser.add_argument("--format", help="output format ([table], path, script, json)")
    parser.add_argument("--select", help="selecton of attributes to be printed (default, [test], minimal, sr, all)")
    parser.add_argument("--sid", help="specify the sid to check for")
    parser.add_argument("--sort", help="specify the column name to sort by")
    #parser.add_argument("--dumpFailures", help="print failed checks per loop",
    #                    action="store_true")
    args = parser.parse_args()
    if args.cib:
        myCluster.config['cib_file'] = args.cib
    if args.format:
        myCluster.config['format'] = args.format
    if args.select:
        myCluster.config['select'] = args.select
    if args.sid:
        myCluster.config['sid'] = args.sid.lower()
    if args.sort:
        if args.sort[0] == '-':
            myCluster.config['sort-reverse'] = True
            myCluster.config['sort'] = args.sort[1:]
        elif args.sort[0] == '+':
            myCluster.config['sort-reverse'] = False
            myCluster.config['sort'] = args.sort[1:]
        else:
            myCluster.config['sort'] = args.sort
    myCluster.xml_import(myCluster.config['cib_file'])
    multi_sid = False
    if myCluster.config['sid'] == None:
        myCluster.get_sids()
        if len(myCluster.sids) == 0:
            print("ERR: No SID found in cluster config")
            sys.exit(1)
        elif len(myCluster.sids) > 1:
            print(f"WARN: Multiple SIDs found in cluster config: {str(myCluster.sids)} Please specify SID using --sid <SID>")
            multi_sid = False
            sys.exit(1)
        else:
           myCluster.config['sid'] = myCluster.sids[0].lower()
    myCluster.fill_glob_dict()
    myCluster.fill_res_dict()
    myCluster.fill_site_dict()
    myCluster.fill_host_dict()
    oformat = "table"
    if 'format' in myCluster.config:
        oformat = myCluster.config['format']
    if oformat == "table":
        index = myCluster.config['sort']
        index_type = 'str'
        index_reverse = myCluster.config['sort-reverse']
        if index == None:
            myCluster.print_dic_as_table(myCluster.glob_dict, "global", "Global")
            myCluster.print_dic_as_table(myCluster.res_dict, "resource", "Resource")
            myCluster.print_dic_as_table(myCluster.site_dict, "site", "Site")
            myCluster.print_dic_as_table(myCluster.host_dict, "host", "Host")
        else:
            myCluster.print_dic_as_table(dict(sorted(myCluster.glob_dict.items(), key=lambda item: (get_sort_value(item[1],index, type=index_type)), reverse=index_reverse)), "global",   "Host")
            myCluster.print_dic_as_table(dict(sorted(myCluster.res_dict.items(),  key=lambda item: (get_sort_value(item[1],index, type=index_type)), reverse=index_reverse)), "resource", "Resource")
            myCluster.print_dic_as_table(dict(sorted(myCluster.site_dict.items(), key=lambda item: (get_sort_value(item[1],index, type=index_type)), reverse=index_reverse)), "site",     "Site")
            myCluster.print_dic_as_table(dict(sorted(myCluster.host_dict.items(), key=lambda item: (get_sort_value(item[1],index, type=index_type)), reverse=index_reverse)), "host",     "Host")
    elif oformat == "json":
        myCluster.print_all_as_json()
    elif oformat == "path" or oformat == "script":
        myCluster.print_dic_as_path(myCluster.glob_dict, "global", "Global", quote='"')
        myCluster.print_dic_as_path(myCluster.res_dict, "resource", "Resource", quote='"')
        myCluster.print_dic_as_path(myCluster.site_dict, "site", "Site", quote='"')
        myCluster.print_dic_as_path(myCluster.host_dict, "host", "Host", quote='"')
    #myCluster.print_dic_as_json(myCluster.host_dict,"Host")


"""
# sort dictionary by nested key-value
print(d)
index = 'status'
index_type = 'str'
index_reverse = False
print("asc: {}".format(dict(sorted(d.items(), key=lambda item: (get_sort_value(item[1],index, type=index_type)), reverse=index_reverse)).keys()))
index_reverse = True
print("des: {}".format(dict(sorted(d.items(), key=lambda item: (get_value(item[1],index, type=index_type)), reverse=index_reverse)).keys()))
# get all configuration-node objects
root.findall("./configuration/nodes/*")
 
# get all node names
for hit in root.findall("./configuration/nodes/*"):
    print(hit.attrib['uname'])

# get a specific configuration-node object
hoef11 = root.findall("./configuration/nodes/*[@uname='hoeferspitze11']")[0]

# get all nvpair objects of a specific configuration-node object
hoef11.findall(".//nvpair")

# alternatively more grammar-specific
hoef11.findall("./instance_attributes/nvpair")

# extract all key=value pairs of a specific configuration-node object
for nv in hoef11.findall("./instance_attributes/nvpair"):
    print(nv.attrib['name'], "=", nv.attrib["value"])

# get all configuration - crm_config - propertysets
root.findall("./configuration/crm_config/cluster_property_set")

# get all nvpair of all configuration - crm_config - propertysets
root.findall("./configuration/crm_config/cluster_property_set/nvpair")

# get all key = value pairs of any nvpair of all configuration - crm_config - propertysets
for nv in root.findall("./configuration/crm_config/cluster_property_set/nvpair"):
    print(nv.attrib['name'], "=", nv.attrib["value"])

########
# configuration  - resources - ( primitive (@id) | clone id=".. | ms id=" ...  )

for res in root.findall("./configuration/resources/*"):
    print(res.tag, nv.attrib)

# find all resources of type SAPHanatopology or SAPHanaController
root.findall("./configuration/resources//*[@type='SAPHanaTopology']")
root.findall("./configuration/resources//*[@type='SAPHanaController']")

# get id of the resource (ms or clone) with type SAPHanaController which has a child with key-value  pair SID=<SID>
root.findall("./configuration/resources//*[@type='SAPHanaController']/instance_attributes/*[@name='SID'][@value='HA1']/../../..")[0].attrib['id']
root.findall("./configuration/resources//*[@type='SAPHanaController']/instance_attributes/nvpair[@name='SID'][@value='HA1']/../../..")[0].attrib['id']

# get all key-value pairs of a specific resource meta-attributes 
res = root.findall("./configuration/resources//*[@type='SAPHanaController']/instance_attributes/nvpair[@name='SID'][@value='HA1']/../../..")[0]
for ma in res.findall("./meta_attributes/nvpair"):
    print(ma.attrib['name'], "=", ma.attrib["value"])

# get all key-value pairs of clone-embedded resources
for nv in res.findall(".//instance_attributes/nvpair"):
    print(nv.attrib['name'], "=", nv.attrib["value"])

# get all meta_attribute key-value pairs of clone-embedded resources (typically empty)
for ma in res.findall("./primitive/meta_attributes/nvpair"):
    print(ma.attrib['name'], "=", ma.attrib["value"])

#############
# cib - rsc_defaults - meta_attributes - nvpair

############
# cib - op_defaults - meta_attributes - nvpair

###########
# cib - status - node_state (uname= ...) - transient_attributes - instance_attributes - nvpair

hoef11 = root.findall("./status/node_state[@uname='hoeferspitze11']")[0]
for nv in hoef11.findall("./transient_attributes/instance_attributes/nvpair"):
   print(nv.attrib['name'], "=", nv.attrib["value"])
"""
