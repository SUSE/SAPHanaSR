#!/usr/bin/python3
# pylint: disable=consider-using-f-string
# pylint: disable=fixme
# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
# pylint: disable=too-many-branches
# pylint: disable=global-variable-undefined
# pylint: disable=too-few-public-methods
# pylint: disable=consider-using-get
# flake8-in-file-ignores: noqa: E501
"""
 saphana_sr_tools.py
 Author:       Fabian Herschel, May 2023
 License:      GNU General Public License (GPL)
 Copyright:    (c) 2023-2025 SUSE LLC

# TODO: STEP01: SID-autodetection - get SID from query for SAPHanaController/SAPHanaTopologyResource - warn, if there are no or more than one SIDs found.
# TODO: STEP02: Think also about multi SID implementation - maybe by using multiple HanaCluster objects (one per SID)
"""

import argparse
# from datetime import datetime
import json
import os
import re
import sys
import subprocess
import xml.etree.ElementTree as ET
import bz2
import datetime
# from dateutil import parser as dateutil_parser

# global lib_version
lib_version = "1.0.20230614.1225"


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
        if kargs['type'] == 'str':
            return ''
    return None


def shorten(column_name, **kargs):
    """ shortens column name
        optinal parameter: sid=<sid> to be more precise in the pattern
        e.g. (1) hana_ha1_site -> site                ( a node attribute)
             (2a) hana_ha1_site_mns_S1 -> mns          ( a site attribute )
             (2b) hana_ha1_site_mns_S_1 -> mns          ( a site attribute, site-name with undersore )
             (3) hana_ha1_global_topology -> topology ( a global attribute )
             (4) master-rsc_SAPHanaCon_HA1_HDB10 -> score
    # TODO: Do we need to check, if the master-attribute belongs to the promotable clone for this SID?
    """
    sid = '...'
    sid_uc = '...'
    if 'sid' in kargs:
        sid = kargs['sid'].lower()
        sid_uc = kargs['sid'].upper()
    match_obj = re.search(f"hana_{sid}_glob_(.*)", column_name)    # (3)
    if match_obj is not None:
        column_name = match_obj.group(1)
    match_obj = re.search(f"hana_{sid}_site_([^_]*)_", column_name)   # (2)
    if match_obj is not None:
        column_name = match_obj.group(1)
    match_obj = re.search(f"hana_{sid}_(.*)", column_name)         # (1)
    if match_obj is not None:
        column_name = match_obj.group(1)
    # TODO: Do we need to check, if the master-attribute belongs to the promotable clone for this SID?
    match_obj = re.search(f"master.rsc.*_{sid_uc}_.*", column_name)   # (4)
    if match_obj is not None:
        column_name = 'score'
    return column_name


class HanaCluster():
    """
    HanaCluster: top level class for an entire cluster
    """

    global selections
    selections = {
                    'all': {
                                    'global': ['.*'],
                                    'resource': ['.*'],
                                    'site': ['.*'],
                                    'host': ['.*'],
                               },
                    'default': {
                                    'global': ['Global', 'timestamp', 'cib-time', 'cib-update', 'dcid', 'maintenance', 'prim', 'sec', 'sid', 'topology'],
                                    'resource': ['Resource', 'maintenance', 'is_managed', 'promotable', 'target_role'],
                                    'site': ['Site', 'lpt', 'lss', 'mns', 'opMode', 'srHook', 'srMode', 'srPoll', 'srr'],
                                    'host': ['Host', 'clone_state', 'node_state', 'roles', 'score', 'site', 'sra', 'srah', 'standby', 'version', 'vhost'],
                               },
                    'sr': {
                                    'global': ['Global', 'cib-time', 'maintenance', 'prim', 'sec', 'sid', 'topology'],
                                    'resource': ['Resource', 'maintenance', 'is_managed', 'promotable'],
                                    'site': ['Site', 'lpt', 'lss', 'mns', 'opMode', 'srHook', 'srMode', 'srPoll', 'srr'],
                                    'host': ['Host', 'clone_state', 'roles', 'score', 'site', 'sra', 'srah', 'vhost'],
                                 },
                    'minimal': {
                                    'global': ['Global', 'cib-time', 'maintenance', 'prim', 'sec', 'sid', 'topology'],
                                    'resource': ['Resource', 'maintenance', 'is_managed'],
                                    'site': ['Site', 'lpt', 'lss', 'mns', 'srHook', 'srPoll', 'srr'],
                                    'host': ['Host', 'clone_state', 'roles', 'score', 'site'],
                                 },
                    'cluster': {
                                    'global': ['Global', 'cib-time', 'cluster-name', 'have-quorum', 'maintenance', 'sid', 'stonith-enabled', 'stonith-timeout', 'stonith-watchdog-timeout', 'topology'],
                                    'resource': ['Resource', 'maintenance', 'is_managed', 'promotable', 'target_role'],
                                    'site': ['Site', 'lpt', 'lss', 'mns', 'opMode', 'srHook', 'srMode', 'srPoll', 'srr'],
                                    'host': ['Host', 'clone_state', 'node_state', 'roles', 'score', 'site', 'sra', 'srah', 'standby', 'vhost'],
                               },
                    'cluster2': {
                                    'global': ['Global', 'cib-time', 'cluster-name', 'have-quorum', 'maintenance', 'sid', 'stonith-enabled', 'stonith-timeout', 'stonith-watchdog-timeout', 'topology'],
                                    'resource': ['Resource', 'maintenance', 'is_managed', 'promotable', 'target_role'],
                                    'site': ['Site', 'lpt', 'lss', 'mns', 'opMode', 'srHook', 'srMode', 'srPoll', 'srr'],
                                    'host': ['Host', 'clone_state', 'node_state', 'roles', 'score', 'site', 'sra', 'srah', 'standby', 'vhost', 'fail.*'],
                               },
                    'cluster3': {
                                    'global': ['-dc.*'],
                                    'resource': ['Resource', 'maintenance', 'is_managed', 'promotable', 'target_role'],
                                    'site': ['Site', 'lpt', 'lss', 'mns', 'opMode', 'srHook', 'srMode', 'srPoll', 'srr'],
                                    'host': ['Host', 'clone_state', 'node_state', 'roles', 'score', 'site', 'sra', 'srah', 'standby', 'vhost', 'fail.*'],
                               },
                    'sitelist': {
                                    'global': [],
                                    'resource': [],
                                    'site': [],
                                    'host': ['site'],
                                },
                    'cmdline': {
                                    'global': [],
                                    'resource': [],
                                    'site': [],
                                    'host': [],
                                },
                }

    def __init__(self):
        """
        initialize an SAP HANA cluster object
        """
        self.multi_status = []
        self.tree = None
        self.root = None
        self.glob_dict = None
        self.res_dict = None
        self.site_dict = None
        self.host_dict = None
        self.selection = 'test'
        self.config = {
            'cib_file': None,
            'cib_file_list': [None],
            'from': 0,
            'format': "table",
            'properties_file': None,
            'select': "default",
            'sid': None,
            'sort': None,
            'sort-reverse': False,
            'to': 99999999999,  # some time in the future ;-)
                      }
        self.sids = []

    def read_properties(self):
        """
        read all properties from json file
        """
        global selections
        if self.config['properties_file']:
            with open(self.config['properties_file'], encoding="utf-8") as prop_fh:
                json_prop = json.load(prop_fh)
                if 'selections' in json_prop:
                    selections = json_prop['selections']
                else:
                    print(f"properties in file {self.config['properties_file']} do not set 'selections'")

    def set_selections(self):
        """
        set_selections - experimental only - might be  changed or deleted without notice
        the selections hash for key 'cmdline' will be overwritten by the config sheme in self.config['show_attributes']
        show_attributes should look like: 'global:attrG1,... resource:attrR1,... site:attrS1,... host:attrH1,...'
        """
        show_attributes = self.config.get('show_attributes', None)
        if show_attributes:
            show_attributes_list = show_attributes.split(' ') # areas are separated by a single blank
            for area_and_attributes in show_attributes_list:
                try:
                    (area_name, attributes) = area_and_attributes.split(':')   # e.g. global:AttributeList
                    attributes_list = attributes.split(',')   # attribute names are separated by comma (',')
                    if area_name == 'global':
                        attributes_list.append('Global')
                    selections['cmdline'].update({area_name: attributes_list})
                except Exception:
                    print(f"show_attributes not formatted correctly ({area_and_attributes})")
                    sys.exit(2)
            print(json.dumps(selections['cmdline']))
        else:
            print("show_attributes not found")
            sys.exit(2)

class HanaStatus():
    """
    HanaStatus: class to capture and analyze an SR status
    """

    def __init__(self, config):
        """
        initialize (SAP) HANA status object
        """
        self.config = config
        self.root = None
        self.tree = None
        self.glob_dict = None
        self.res_dict = None
        self.site_dict = None
        self.host_dict = None
        self.sids = None

    def xml_import(self, filename):
        """
        xml_import - import a cluster CIB into object dictionaries
        """
        if filename is None:
            # use cibadmin as input
            cmd = "cibadmin -Ql"
            try:
                xml_string = subprocess.check_output(cmd.split(" "))
                self.root = ET.fromstring(xml_string)
            except FileNotFoundError as f_err:
                print(f"Could not call {cmd}: {f_err}")
        elif filename == "-":
            # read from stdin
            self.tree = ET.parse(sys.stdin)
            self.root = self.tree.getroot()
        else:
            # read from filename
            if os.path.isfile(filename):
                # bz2 ?
                match_obj = re.search(r"\.bz2$", filename)
                if match_obj:
                    print(f"File {filename} ending with .bz2 is assumed to be compressed with bzip2 - try to uncompress")
                    with bz2.open(filename, "rb") as f:
                        content = f.read()
                    self.root = ET.fromstring(content.decode())
                else:
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
        self.glob_dict = {"global": {}}
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
            global_glob_dict.update({'cib-last-written': cib_attrs["cib-last-written"]})
        if 'have-quorum' in cib_attrs:
            global_glob_dict.update({'have-quorum': cib_attrs["have-quorum"]})
        # TODO: for live cib the execution-date does not exist. use system time 'now' instead
        if 'execution-date' in cib_attrs:
            global_glob_dict.update({'timestamp': cib_attrs["execution-date"]})
            s_cib_timestamp = cib_attrs["execution-date"]
            s_cib_time_fmt = datetime.datetime.utcfromtimestamp(int(s_cib_timestamp))
            global_glob_dict.update({'cib-time': s_cib_time_fmt.strftime('%Y-%m-%dT%H:%M:%S')})
        if 'admin_epoch' in cib_attrs and 'num_updates' in cib_attrs and 'epoch' in cib_attrs:
            global_glob_dict.update({'cib-update': f'{cib_attrs["admin_epoch"]}.{cib_attrs["epoch"]}.{cib_attrs["num_updates"]}'})
        if 'dc-uuid' in cib_attrs:
            global_glob_dict.update({'dcid': cib_attrs["dc-uuid"]})

    def fill_res_dict(self):
        """
        fill_res_dict() - fill the 'resource' dictionary
        TODO: Controller and Topology part very similar -> create a method for processing that
        """
        sid = self.config["sid"].upper()
        self.res_dict = {}
        # Controller
        con_res_arr = self.root.findall(f"./configuration/resources//*[@type='SAPHanaController']/instance_attributes/nvpair[@name='SID'][@value='{sid}']/../../..")
        if len(con_res_arr) == 0:
            con_res_arr = self.root.findall(f"./configuration/resources//*[@type='SAPHana']/instance_attributes/nvpair[@name='SID'][@value='{sid}']/../../..")
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
            sid = self.get_sid_from_attribute(name)
            if site and sid == self.config['sid']:
                if site not in self.site_dict:
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
                    node_table.update({shorten(name, sid=sid): value})
            else:
                node_table.update({shorten(name): value})
        host_status_obj_all = self.root.findall(f"./status/node_state[@uname='{hostname}']")
        if len(host_status_obj_all) > 0:
            host_status_obj = host_status_obj_all[0]
            hostcrmd = host_status_obj.attrib['crmd']
            node_table.update({'crmd': hostcrmd})
            for nv in host_status_obj.findall("./transient_attributes/instance_attributes/nvpair"):
                name = nv.attrib['name']
                value = nv.attrib["value"]
                if self.is_hana_attribute(name):
                    sid = self.get_sid_from_attribute(name)
                    if sid == self.config['sid']:
                        node_table.update({shorten(name, sid=sid): value})
                else:
                    node_table.update({shorten(name, sid=self.config['sid']): value})

    def is_site_attribute(self, column_name, **kargs):
        """
        TODO: description
        """
        return_site_name = False
        if 'return_site_name' in kargs:
            return_site_name = kargs['return_site_name']
        match_obj = re.search("hana_..._site_[^_]*_(.*)", column_name)
        if match_obj:
            if return_site_name:
                return match_obj.group(1)
            return True
        if return_site_name:
            return None
        return False

    def is_hana_attribute(self, name):
        """
        TODO: description
        """
        match_obj = re.match("hana_.*", name)
        if match_obj:
            return True
        return False

    def is_hana_glob_attribute(self, name):
        """
        TODO: description
        """
        match_obj = re.match("hana_..._glob_.*", name)
        if match_obj:
            return True
        return False

    def get_sid_from_attribute(self, name):
        """
        TODO: description
        """
        sid = None
        match_obj = re.match("hana_(...)_", name)
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
        new_line = 0
        for col in column_names:
            if self.filter(area, col) is True:
                if col in column_length:
                    col_len = column_length[col]
                else:
                    col_len = 1
                print("{0:<{width}} ".format(shorten(col), width=col_len), end='')
                new_line = 1
                bar_len += col_len + 1
        if new_line:
            print()
            print('-' * bar_len)
        #
        # print rows
        #
        for key in print_dic:
            new_line = 0
            for col in column_names[0:]:
                if self.filter(area, col) is True:
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
                    new_line = 1
            if new_line:
                print()
        if new_line:
            print()

    def print_dic_as_table_sort_by(self, dic, index, index_type, index_reverse, area, table_name):
        """
        print_dic_as_table_sort_by - print a dictionary 'table' sorted by 'index'
        """
        self.print_dic_as_table(dict(sorted(dic.items(), key=lambda item: (get_sort_value(item[1], index, type=index_type)), reverse=index_reverse)), area, table_name)

    def print_dic_as_json(self, print_dic, table_name):
        """
        TODO: description
        """
        json_obj = json.dumps({table_name: print_dic}, indent=4)
        print(json_obj)

    def print_all_as_json(self):
        """
        TODO: description
        """
        # TODO: maybe 'Global', 'Site', 'Host", ... configurable strings?
        json_obj = json.dumps({
                                 'Global': self.glob_dict,
                                 'Resource': self.res_dict,
                                 'Site': self.site_dict,
                                 'Host': self.host_dict
                              }, indent=4
                              )
        print(json_obj)

    def print_dic_as_path(self, print_dic, area, table_name, **kargs):
        """
        TODO: description
        """
        time_string = ""
        quote = ''
        if 'quote' in kargs:
            quote = kargs['quote']
        if 'ts' in kargs:
            time_string = f"{kargs['ts']} "
        for key in print_dic:
            for col in print_dic[key]:
                if self.filter(area, col) is True:
                    value = print_dic[key][col]
                    print(f"{time_string}{table_name}/{key}/{col}={quote}{value}{quote}")

    def print_dic_as_csv(self, print_dic, area, table_name, **kargs):
        """
        TODO: description
        """
        time_string = ""
        quote = ''
        short = False
        if 'quote' in kargs:
            quote = kargs['quote']
        if 'ts' in kargs:
            time_string = f"{kargs['ts']} "
        if 'short' in kargs:
            short = kargs['short']
        for key in print_dic:
            for col in print_dic[key]:
                if self.filter(area, col) is True:
                    value = print_dic[key][col]
                    if short:
                        print(f"{key}:{quote}{value}{quote}")
                    else:
                        #print(f"{time_string}{table_name}/{key}/{col}={quote}{value}{quote}")
                        print(f"{table_name}:{key}:{col}:{quote}{value}{quote}")

    def filter(self, area, column_name):
        ''' filter column_names
            False, if column should be skipped
            True, if column should be printed
        '''
        select = self.config['select']
        if select in selections and area in selections[select]:
            the_selection = selections[select][area]
            after_loop = False
            for pat in the_selection:
                on_match = True
                if pat[0] == '-':
                    after_loop = True
                    on_match = False
                    pat = pat[1:]
                elif pat[0] == '+':
                    pat = pat[1:]
                match_obj = re.match(pat + '$', column_name)
                if match_obj:
                    return on_match
            return after_loop
        return True

    def get_sids(self):
        """
        get_sids - ger als SIDs mentioned in a SAPHanaController resource
        """
        root = self.root
        sids = []
        try:
            for ia in root.findall("./configuration/resources//*[@type='SAPHanaController']/instance_attributes/nvpair[@name='SID']"):
                sids.append(ia.attrib['value'])
            for ia in root.findall("./configuration/resources//*[@type='SAPHana']/instance_attributes/nvpair[@name='SID']"):
                sids.append(ia.attrib['value'])
        except AttributeError:
            print(f"Could not find any SAPHanaController resource in cluster config")
        self.sids = sids


if __name__ == "__main__":
    myCluster = HanaCluster()
    parser = argparse.ArgumentParser()
    parser.add_argument("--cib", help="specify the cibfile file")
    args = parser.parse_args()
    if args.cib:
        myCluster.config['cib_file_list'] = args.cib
    print(f"dbg: {myCluster.config['cib_file_list']}")
    cib_file = myCluster.config['cib_file_list']
    print(f"dbg: {cib_file}")
    myHana = HanaStatus(myCluster.config)
    myHana.xml_import(cib_file)
    multi_sid = False
    if myCluster.config['sid'] is None:
        myHana.get_sids()
        if len(myHana.sids) == 0:
            print("ERR: No SID found in cluster config")
            sys.exit(1)
        elif len(myHana.sids) > 1:
            print(f"WARN: Multiple SIDs found in cluster config: {str(myCluster.sids)} Please specify SID using --sid <SID>")
            multi_sid = False
            sys.exit(1)
        else:
            myHana.config['sid'] = myHana.sids[0].lower()
            myCluster.config['sid'] = myHana.sids[0].lower()
    myHana.fill_glob_dict()
    myHana.fill_res_dict()
    myHana.fill_site_dict()
    myHana.fill_host_dict()
    myHana.print_dic_as_table(myHana.glob_dict, "global", "Global")
    myHana.print_dic_as_table(myHana.res_dict, "resource", "Resource")
    myHana.print_dic_as_table(myHana.site_dict, "site", "Site")
    myHana.print_dic_as_table(myHana.host_dict, "host", "Host")
