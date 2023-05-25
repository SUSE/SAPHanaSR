import xml.etree.ElementTree as ET
import re
import json

class HanaCluster():

    selections = {
                    'default': {
                                    'global'   : ['cib-time', 'maintenance', 'prim', 'sec', 'topology'],
                                    'resource' : ['maintenance', 'is_managed'],
                                    'site'     : ['lpt', 'lss', 'mns', 'opMode', 'srHook', 'srMode', 'srPoll', 'srr'],
                                    'host'     : ['clone_state', 'node_state', 'roles', 'score', 'site', 'sra', 'srah', 'standby', 'version', 'vhost'],
                               },
                    'sr': {
                                    'global'   : ['cib-time', 'maintenance', 'prim', 'sec', 'topology'],
                                    'resource' : ['maintenance', 'is_managed'],
                                    'site'     : ['lpt', 'lss', 'mns', 'opMode', 'srHook', 'srMode', 'srPoll', 'srr'],
                                    'host'     : ['clone_state', 'roles', 'score', 'site', 'sra', 'srah', 'vhost'],
                                 },
                    'minimal': {
                                    'global'   : ['cib-time', 'maintenance', 'topology'],
                                    'resource' : ['maintenance', 'is_managed'],
                                    'site'     : ['lpt', 'lss', 'mns', 'srHook', 'srPoll', 'srr'],
                                    'host'     : ['clone_state', 'roles', 'score', 'site'],
                                 }
                }


    def __init__(self):
        self.tree = None
        self.root = None
        self.global_table = None
        self.resource_table = None
        self.site_table = None
        self.host_table = None

    def xml_import(self, filename):
        self.tree = ET.parse(filename)
        self.root = self.tree.getroot()

    def fill_host_table(self):
        self.host_table = {}
        for host_obj in self.root.findall("./configuration/nodes/*"):
            hostname = host_obj.attrib['uname']
            self.host_table.update({hostname: {}})
            node_table = self.host_table[hostname]
            self.fill_node(hostname, node_table)
            #print(self.host_table)

    def fill_node(self, hostname, node_table):
        host_obj = self.root.findall(f"./configuration/nodes/*[@uname='{hostname}']")[0]
        for nv in host_obj.findall("./instance_attributes/nvpair"):
            node_table.update({nv.attrib['name']: nv.attrib["value"]})
        host_status_obj = self.root.findall(f"./status/node_state[@uname='{hostname}']")[0]
        for nv in host_status_obj.findall("./transient_attributes/instance_attributes/nvpair"):
           node_table.update({nv.attrib['name']: nv.attrib["value"]})

    def shorten(self, column_name):
        """ shortens column name
            e.g. (1) hana_ha1_site -> site              ( a node attribute)
                 (2) hana_ha1_site_mns_S1 -> mns        ( a site attribute )
                 (3) hana_ha1_global_topology -> global ( a global attribute )
        """
        match_obj = re.search("hana_..._global_(.*)",column_name)  # (3)
        if match_obj != None:
            column_name = match_obj.group(1)
        match_obj = re.search("hana_..._site_(.*)_",column_name)   # (2)
        if match_obj != None:
            column_name = match_obj.group(1)
        match_obj = re.search("hana_..._(.*)",column_name)         # (1)
        if match_obj != None:
            column_name = match_obj.group(1)
        return column_name

    def print_dic_as_table(self, print_dic, table_name):
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
            col_len = len(self.shorten(col)) 
            for key in print_dic:
                if col in print_dic[key]:
                    col_len = max(col_len, len(print_dic[key][col]))
            column_length[col] = col_len
        #
        # print headline
        #
        for col in column_names:                 # later add 'filter' for column names
            if self.filter(col) == True:
                if col in column_length:
                    col_len = column_length[col]
                else:
                    col_len = 1
                print("{0:<{width}} ".format(self.shorten(col), width=col_len), end='')
        print()
        #
        # print rows
        #
        for key in print_dic:
            for col in column_names[0:]:        
                if self.filter(col) == True:
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

    def print_dic_as_json(self, print_dic, table_name):
        json_obj = json.dumps({table_name: print_dic}, indent = 4)
        print(json_obj)

    def print_dic_as_path(self, print_dic, table_name, **kargs):
        quote=''
        if 'quote' in kargs:
            quote = kargs['quote']
        for key in print_dic:
            for col in print_dic[key]:
                if self.filter(col) == True:
                    value = print_dic[key][col]
                    print(f"{table_name}/{key}/{col}={quote}{value}{quote}")
                
    def filter(self, column_name):
        ''' filter column_names 
            False, if column should be skipped
            True, if column should be printed
            TODO: implement filter sets e.g. all, default, sr, ...
            TODO: filter sets might allow custom config via json file (filter set per area)
        '''
        match_obj = re.search("#feature",column_name)
        if match_obj != None:
            return False
        match_obj = re.search("fail-count-",column_name) 
        if match_obj != None:
            return False
        match_obj = re.search("last-failure-",column_name) 
        if match_obj != None:
            return False
        return True


myCluster = HanaCluster()
myCluster.xml_import('hoef.test.xml')
myCluster.fill_host_table()
myCluster.print_dic_as_table(myCluster.host_table,"Host")
myCluster.print_dic_as_json(myCluster.host_table,"Host")
myCluster.print_dic_as_path(myCluster.host_table,"Host", quote='"')


"""
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
