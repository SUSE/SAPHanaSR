import xml.etree.ElementTree as ET

class HanaCluster():

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
        for host_obj in self.root.findall("./configuration/nodes/*"):
            hostname = host_obj.attrib['uname']
            self.fill_node(hostname)

    def fill_node(self, hostname):
        print(f"===== host: {hostname} =====")
        host_obj = self.root.findall(f"./configuration/nodes/*[@uname='{hostname}']")[0]
        for nv in host_obj.findall("./instance_attributes/nvpair"):
            print(nv.attrib['name'], "=", nv.attrib["value"])
        host_status_obj = self.root.findall(f"./status/node_state[@uname='{hostname}']")[0]
        for nv in host_status_obj.findall("./transient_attributes/instance_attributes/nvpair"):
           print(nv.attrib['name'], "=", nv.attrib["value"])


myCluster = HanaCluster()
myCluster.xml_import('hoef.test.xml')
myCluster.fill_host_table()


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
