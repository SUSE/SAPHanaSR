#
#
# SAPHanaSRTools.pm
# Copyright:    (c) 2014 SUSE Linux Products GmbH
# Copyright:    (c) 2015-2016 SUSE Linux GmbH
# Copyright:    (c) 2017-2022 SUSE LLC
# Author: Fabian Herschel
# License: Check if we publish that under GPL v2+
# Version: 0.28.2024.12.12
#
##################################################################

package SAPHanaSRTools;
require Exporter;
use POSIX;

use strict;

use Sys::Syslog;
use Sys::Hostname;
use File::Path;
use vars qw(@ISA @EXPORT @EXPORT_OK);
# use Data::Dumper qw(Dumper);
@ISA = qw(Exporter);
# Init immediately so their contents can be used in the 'use vars' below.
@EXPORT    = qw(
    check_lpa_status
    check_all_ok
    check_node_status
    check_node_mode
    get_hana_attributes
    get_hana_sync_state
    get_lpa_by_host
    get_nodes_online
    get_node_status
    get_sid_and_InstNr
    get_number_primary
    get_number_secondary
    get_host_primary
    get_host_secondary
    get_new_attribute_model
    get_number_HANA_standby
    get_HANA_nodes
    get_node_list
    get_master_nameserver
    get_site_by_host
    host_attr2string
    insertAttribute
    max
    max get_nodes_online
    mysyslog
    mysyslog
    path_to_table
    print_host_attr
    set_new_attribute_model
    set_cibFile
    set_Host
    set_GName
    set_HName
    set_SName
    set_Site
    set_Global
);


my $VERSION="1.0";
my $newAttributeModel=0;
my $cibFile="";

my %selections = (
                    'default' => {
                                    'global'   => ["cib-time", "maintenance", "prim", "sec", "topology"],
                                    'resource' => ["maintenance", "is_managed"],
                                    'site'     => ["lpt", "lss", "mns", "opMode", "srHook", "srMode", "srPoll", "srr"],
                                    'host'     => ["clone_state", "node_state", "roles", "score", "site", "sra", "srah", "standby", "version", "vhost"],
                                 },
                    'sr' => {
                                    'global'   => ["cib-time", "maintenance", "prim", "sec", "topology"],
                                    'resource' => ["maintenance", "is_managed"],
                                    'site'     => ["lpt", "lss", "mns", "opMode", "srHook", "srMode", "srPoll", "srr"],
                                    'host'     => ["clone_state", "roles", "score", "site", "sra", "srah", "vhost"],
                                 },
                    'minimal' => {
                                    'global'   => ["cib-time", "maintenance", "topology"],
                                    'resource' => ["maintenance", "is_managed"],
                                    'site'     => ["lpt", "lss", "mns", "srHook", "srPoll", "srr"],
                                    'host'     => ["clone_state", "roles", "score", "site"],
                                 }
                 );

#    @EXPORT_OK    = qw(max  mysyslog get_nodes_online);

# The X-Hashes     contain the structure OBJECT -> ATTRIBUTE (KEY) - VALUE
# The XName-Hashes contain the structure ATTRIBUTE (KEY) -> OBJECT - VALUE
#
# Depending on the hashes OBJECT could be sid, node-name, site-name, resource-id
# ATTRIBUTES could be clone_state, srHook
#
# There are xxx types of hashes:
#
# G and GName: Hashes for global attribues (object is always "<SID>")
# H and HName: Hashes for the host specific attributes (objects are host-names)
# R and RName: Hashes for the resource specific attributes (object are resource-names)
# S and SName: Hashes for the site specific attributes (objects are site-names)
#
#
#

my $refGlobal;
my $refGName;  # reference to GlobalTableKeyName Hash attribute -> object - value
my $refHName;  # reference to HostTableKeyName Hash
my $refSName;  # reference to SiteTableKeyName Hash
my $refRName;  # reference to ResourceTableKeyName Hash
my $refSite;   # reference to Site-Hash
my $refHost;   # reference to Host-Hash

sub set_Site
{
   $refSite=shift();
}
sub set_Host
{
   $refHost=shift();
}
sub set_HName
{
   $refHName=shift();
}
sub set_GName
{
   $refGName=shift();
}
sub set_Global
{
   $refGlobal=shift();
}
sub set_RName
{
   $refRName=shift();
}
sub set_SName
{
   $refSName=shift();
}

sub set_new_attribute_model
{
    $newAttributeModel=1;
}

sub set_cibFile
{
    $cibFile=shift();
}

sub get_new_attribute_model
{
    return $newAttributeModel;
}

sub attr_in_selection {
    my $result = 0;
    my ($testSelection, $testArea, $testAttr ) = @_;
    if ( $testAttr =~ /hana_..._(.*)/ ) {
       $testAttr =  $1;
    }
    if ( $testSelection eq "all" ) {
        $result=1;
    } else {
        if ( exists($selections{$testSelection})) {
            my @sel_def_site = @{$selections{$testSelection}->{$testArea}};
            if ( grep /^$testAttr$/, @sel_def_site ) {
                $result=1
            } else {
                # print "filtered: testSelection=$testSelection, testArea=$testArea, testAttr=$testAttr ", join(":",@sel_def_site), " \n";
            }
            #$result=1 if grep /^$testAttr$/, @sel_def_site ;
        } else {
            $result=0;
        }
    }
    return $result;
}

sub max {
    # thanks to http://www.perlunity.de/perl/forum/thread_018329.shtml
    my $a = shift;
    my $b = shift;
    return $a > $b ? $a : $b;
}

sub mysyslog {
   my ($prio, $form, @param) = ( @_ );
   syslog $prio, $form, @param;
}

sub get_nodes_online
{
    my $result=0;
    my $sid=shift;
    my $result="";
    foreach my $h ( keys(%{$$refHName{node_state}}) ) {
        if ( not ($h =~ "^_[lt]") ) {
            if ( get_node_status($h) eq "online" || get_node_status($h) =~ /^\d\d\d+$/ ) {
                $result++;
            }
        }
    }
    return $result;
}

sub get_node_status
{
    # typically returns online, standby or offline
    # since pacemaker ?? online/offile and standby (on/off) are 2 different attributes
    my $result="offline";
    my $node=shift;
    my $standby;
    $result=$$refHName{"node_state"}->{$node};
    # printf("DBG: node %s node_state %s standby %s\n", $node, $result, $$refHName{"standby"}->{$node});
    if ( defined ($$refHName{"standby"}->{$node})) {
       $standby = $$refHName{"standby"}->{$node};
       if ( $standby eq "on" ) {
           $result="standby";
       }
    }
    return $result;
}

sub get_node_list
{
    # crm_node -l | awk '$3 == "member" { if ($2 != me) { print $2 }}'
    my @nodes;
    foreach my $h ( keys(%{$$refHName{node_state}}) ) {
        if ( ! ( $h =~ "^_" )) {
            push (@nodes, $h);
        }
    }
    return @nodes;
}

#
# works only, if ONE SAPinstance (here HANA) is installed on the cluster
#
sub get_sid_and_InstNr
{
    my $sid=""; my $Inr=""; my $noDAACount = 0; my $gotAnswer = 0;
    my @sid_ino;
    open my $ListInstances, "-|", "/usr/sap/hostctrl/exe/saphostctrl -function ListInstances";
    while (<$ListInstances>) {
        # try to catch:  Inst Info : LNX - 42 - lv9041 - 740, patch 36, changelist 1444691
        chomp;
        if ( /^[^:]+:\s*(\w+)\s*-\s*(\w+)\s*-/ ) {
            $gotAnswer = 1;
            my $foundSID=$1;
            my $foundINO=$2;
            if ( $foundSID ne "DAA" ) {
                $noDAACount++;
                $sid=lc($foundSID);
                $Inr=$foundINO;
                push @sid_ino, "$sid:$Inr";
            }
        }
#       if ( $_ =~ /:\s+([A-Z][A-Z0-9][A-Z0-9])\s+-\s+([0-9][0-9])/ ) {
#          $sid=lc("$1");
#          $Inr=$2;
    }
    close ListInstances;
    #printf (" get_sid_and_InstNr: return (%s)\n", join(",", ( $sid, $Inr, $noDAACount, $gotAnswer )));
    $sid=join(",", @sid_ino);
    return ( $sid, $noDAACount, $gotAnswer );
}

my $table_title = "Host \\ Attr";

sub insertAttribute {
    my ($sid, $refHash, $refN, $object, $attribute, $value) = @_;
    my $table_titleH="";
    if ( $attribute =~ /hana_${sid}_(.*)/ ) {
       $attribute =  $1;
    }
       #
       # handle the hosts name and table-title
       #
       $$refHash{$object}->{$attribute}=${value};
       if ( defined ($$refN{_hosts}->{_length})) {
          $$refN{_hosts}->{_length} = max($$refN{_hosts}->{_length}, length($object ));
       } else {
          $$refN{_hosts}->{_length} = length($object );
       }
       $$refN{_hosts}->{_length} = max($$refN{_hosts}->{_length}, length( $table_titleH));
       #
       # now handle the attributes name and value
       #
       $$refN{$attribute}->{$object}=${value};
    #   $$refN{$attribute}->{$object}=${value};
       if ( defined ($$refN{$attribute}->{_length})) {
          $$refN{$attribute}->{_length} = max($$refN{$attribute}->{_length}, length($value ));
       } else {
          $$refN{$attribute}->{_length} = length($value );
       }
       $$refN{$attribute}->{_title} = $attribute;
       $$refN{$attribute}->{_length} = max($$refN{$attribute}->{_length}, length( $$refN{$attribute}->{_title}));
       # printf "%-8s %-20s %-30s\n", $1, $2, $3;
}
################
sub get_hana_attributes
{
    my ($sid, $refHH, $refHN, $refGL, $refGN, $refST, $refSN, $refRL, $refRN, $selection ) = @_;
    my %id2uname;
    my $CIB;
    if ( !defined ($selection)) {
        $selection = "all";
    }
    if ( $cibFile eq "" ) {
        open $CIB, "-|", "cibadmin -Ql" or die "CIB could not be read from cluster";
    } else  {
       open $CIB, "<", "$cibFile" or die "CIB file $cibFile not found or not able to read it";
    }
    insertAttribute($sid, $refGL, $refGN, "global", "sid", uc($sid));
    while (<$CIB>) {
        chomp;
        my ($host, $name, $site, $value);
        if ( $_ =~ /cib-last-written="([^"]*)"/ ) {
            # printf "CIB-time: %s\n", $1;
            if ( attr_in_selection($selection, "global", "cib-time") ) {
                insertAttribute($sid, $refGL, $refGN, "global", "cib-time", $1);
            }
        }
        # search for is-managed and maintenance attributes
        my $id, $value;
        if ( / name=\"?(is-managed|maintenance)\"?/ ) {
            $name = $1;
            if ( / id="([^\"]*)"/ ) {
                $id=$1;
                if ( $id =~ /([^-]*)-/ ) {
                    $id=$1;
                }
            }
            if ( / value="([^\"]*)"/ ) {
                $value=$1;
            }
            if ( $id eq "cib" ) {
                if ( attr_in_selection($selection, "global", "$name") ) {
                    insertAttribute($sid, $refGL, $refGN, "global", "$name", "$value");
                }
            } elsif ( $id eq "nodes" ) {
                # to be processed in node section (below)
            } else {
                if ( attr_in_selection($selection, "resource", "$name") ) {
                    insertAttribute($sid, $refRL, $refRN, "$id", "$name", "$value");
                }
            }
        }
        my $SID=uc($sid);
        if ( $_ =~ /<node / ) {
            # catch a node definition line
            my $nodeID="";
            my $nodeUNAME="";
            if ( $_ =~ /id="([^"]+)"/ ) {
                $nodeID=$1;
            }
            if ( $_ =~ /uname="([^"].+)"/ ) {
                $nodeUNAME=$1;
            }
            if (($nodeID ne "") && ($nodeUNAME ne "")) {
                $id2uname{$nodeID}=$nodeUNAME;
                # printf STDERR "%s -> %s\n", $nodeID, $id2uname{$nodeID};
            }
        }
        #
        #  <nvpair id="nodes-1234567890-standby" name="standby" value="off"/>
        #
        if ( $_ =~ /id="nodes-(.+)-(standby|maintenance)"/ ) {
            my $host=$1; my $attribute=$2;
            if (defined $id2uname{$host}) {
                $host = $id2uname{$host}
            }
            if ( $_ =~ /value="([a-zA-Z0-9\-\_]+)"/ ) {
                my $value=$1;
                #printf "STANDBY <%s> VALUE <%s>\n", $host, $value;
                if ( attr_in_selection($selection, "host", "$attribute") ) {
                    insertAttribute($sid, $refHH, $refHN, $host, $attribute, $value);
                }
            }
        }
        #
        #  <node_state id="1234567890" uname="node01" in_ccm="true" crmd="online" crm-debug-origin="do_update_resource" join="member" expected="member">
        #
        #if ( $_ =~ /node_state id=".+" uname="([a-zA-Z0-9\-\_]+)" .*crmd="([a-zA-Z0-9\-\_]+)"/ ) {
        #    # insertAttribute($sid, \%Host, \%HName, $1, "node_status", $2);
        #    insertAttribute($sid, $refHH, $refHN, $1, "node_status", $2);
        #}
        if ( $_ =~ /nvpair.*name="([a-zA-Z0-9\_\-]+_${sid}_([a-zA-Z0-9\-\_]+)|(terminate))"/) {
            $name=$1;
            # Bug 1192963 - L3: SAPHanaSR-monitor not reporting correctly
            #  - catch also ids: id="host15-instance_attributes-hana_ha1_srmode"
            #
            if (( $_ =~ /id=.((.*)-instance_attributes)-([a-zA-Z0-9\_\-]+)/ )
                || ( $_ =~ /id=.(status|nodes)-([a-zA-Z0-9\_\-]+)-/ )) {
                # found attribute in nodes forever and reboot store
                $host=$2;
                if (defined $id2uname{$host}) {
                    $host = $id2uname{$host}
                }
                if ( $_ =~ /value="([^"]+)"/ ) {
                    $value=$1;
                    # printf "insert $sid HOST $host $name $value\n";
                    if ( attr_in_selection($selection, "host", "$name") ) {
                        insertAttribute($sid, $refHH, $refHN, $host, $name, $value);
                    }
                }
            } elsif ( $_ =~ /id=.SAPHanaSR-[a-zA-Z0-9\_\-]+_site_[a-zA-Z0-9\-]+_([a-zA-Z0-9\_\-]+)/) {
                # found a site attribute
                $site=$1;
                if ( $name =~ /[a-zA-Z0-9\_\-]+_site_([a-zA-Z0-9\-]+)/ ) {
                    $name = $1;
                }
                if ( $_ =~ /value="([^"]+)"/ ) {
                    $value=$1;
                    if ( attr_in_selection($selection, "site", "$name") ) {
                        insertAttribute($sid, $refST, $refSN, $site, $name, $value);
                    }
                }
            } elsif ( $_ =~ /id=.SAPHanaSR-[a-zA-Z0-9\_\-]+_glob_[a-zA-Z0-9\_\-]+/) {
                # found a global attribute
                $host="GLOBAL";
                if ( $name =~ /([a-zA-Z0-9\_\-]+)_glob_([a-zA-Z0-9\_\-]+)/ ) {
                    $name = $2;
                }
                if ( $_ =~ /value="([^"]+)"/ ) {
                    $value=$1;
                    if ( attr_in_selection($selection, "global", "$name") ) {
                     insertAttribute($sid, $refGL, $refGN, "global", $name, $value);
                    }
                }
            }
        } elsif ( $_ =~ /nvpair.*name="master.([a-zA-Z0-9\_\-]+_${SID}_([a-zA-Z0-9\-\_]+))"/ ) {
            # lines with master scores:
            # <nvpair id="status-suse05-master-rsc_SAPHanaCon_HA1_HDB10" name="master-rsc_SAPHanaCon_HA1_HDB10" value="150"/>
            $name="score";
            if ( $_ =~ /id=.status-([a-zA-Z0-9\_\-]+)-master/ ) {
                # found attribute in nodes forever and reboot store
                $host=$1;
                if (defined $id2uname{$host}) {
                    $host = $id2uname{$host}
                }
                if ( $_ =~ /value="([^"]+)"/ ) {
                    $value=$1;
                    # printf "insert $sid HOST $host $name $value\n";
                    if ( attr_in_selection($selection, "host", "$name") ) {
                        insertAttribute($sid, $refHH, $refHN, $host, $name, $value);
                    }
                }
            }
        } elsif ( $_ =~ /node_state.* crmd="([a-zA-Z0-9\-\_]+)"/ ) {
            my $name = "node_state";
            my $value = $1;
            if ( $_ =~ /node_state.* uname="([a-zA-Z0-9\-\_]+)"/ ) {
                my $host = $1;
                if ( attr_in_selection($selection, "host", "$name") ) {
                    insertAttribute($sid, $refHH, $refHN, $host, $name, $value);
                }
            }
        }
    }
    close CIB;
    return 0;
}

################

#
# path_to_table
# converts output in path form (<table>/<object>i/<key>="<value>") into hashes which can be output by print_host_attr()
# table could (for first) be one of ['Global','Resource','Sites','Hosts']
sub path_to_table
{
    my ($sid, $refHH, $refHN, $refGL, $refGN, $refST, $refSN, $refRL, $refRN, $selection ) = @_;
    #
    # for first we take plain stdin to parse the path lines
    #
    while  (<>) {
        chomp();
        # <table>/<object>i/<key>="<value>"
        if ( $_ =~ m|([^/]*)/([^/]*)/([^/]*)="?([^"]*)"?| ) {
            my ( $table, $object, $key, $value ) = ( $1, $2, $3, $4 );
            if ( $table eq "Global" ) {
                if ( attr_in_selection($selection, "global", "$key") ) {
                    insertAttribute($sid, $refGL, $refGN, $object, $key, $value);
                }
            } elsif ( $table eq "Resource" ) {
                if ( attr_in_selection($selection, "resource", "$key") ) {
                    insertAttribute($sid, $refRL, $refRN, $object, $key, $value);
                }
            } elsif ( $table eq "Sites" ) {
                if ( attr_in_selection($selection, "site", "$key") ) {
                    insertAttribute($sid, $refST, $refSN, $object, $key, $value);
                }
            } elsif ( $table eq "Hosts" ) {
                if ( attr_in_selection($selection, "host", "$key") ) {
                    insertAttribute($sid, $refHH, $refHN, $object, $key, $value);
                }
            }
        } else {
            printf("DBG: not a path: %s\n", $_);
        }
    }
}

sub get_hana_sync_state_old # by global / sync_state
{
    my $sid=shift;
    my $result="";
    if ( $newAttributeModel == 1 ) {
        $result = $$refGName{sync_state}->{"global"};
    } else  {
        foreach my $h ( keys(%{$$refHName{sync_state}}) ) {
            if ( $$refHName{sync_state}->{$h} =~ /(S.*)/ ) {
               $result=$1;
            }
        }
    }
    return $result;
}

sub get_hana_sync_state
{
    my $result="-";
    if ( $newAttributeModel == 1 ) {
        foreach my $s ( keys(%{$$refSName{"srr"}}) ) {
            if ( $$refSName{"srr"}->{$s} =~ /S/ ) {
                $result = $$refSName{"srHook"}->{$s}; 
		# TODO: fall-back to srPoll, id result is SWAIT
            }
        }
    } else  {
        foreach my $h ( keys(%{$$refHName{"roles"}}) ) {
            if ( $$refHName{"roles"}->{$h} =~ /[0-9]:S:/ ) {
                $result = $$refHName{"score"}->{$h};
            }
        }
    }
    return $result;
}

sub get_secondary_score
{
    my $result="-";
    if ( $newAttributeModel == 1 ) {
        foreach my $s ( keys(%{$$refSName{"srr"}}) ) {
# TODO
            $result="-";
            #if ( ( $$refSName{"srr"}->{$s} =~ /P/ ) && ( $$refSName{"lss"}->{$s} =~ /[$lss]/ )) {
            #   $rc++;
            #}
        }
    } else  {
        foreach my $h ( keys(%{$$refHName{"roles"}}) ) {
            if ( $$refHName{"roles"}->{$h} =~ /[0-9]:S:/ ) {
                $result = $$refHName{"score"}->{$h};
            }
        }
    }
    return $result;
}

sub get_number_primary
{
    my $sid=shift;
    my $lss=shift;
    my $rc=0;
    if ( $newAttributeModel == 1 ) {
        foreach my $s ( keys(%{$$refSName{"srr"}}) ) {
            if ( ( $$refSName{"srr"}->{$s} =~ /P/ ) && ( $$refSName{"lss"}->{$s} =~ /[$lss]/ )) {
               $rc++;
            }
        }
    } else  {
        foreach my $h ( keys(%{$$refHName{"roles"}}) ) {
            if ( $$refHName{"roles"}->{$h} =~ /[$lss]:P:/ ) {
               $rc++;
            }
        }
    }
    return $rc;
}

sub get_number_HANA_standby
{
    my $sid=shift;
    my $site=shift;
    my $standby=0;
    if ( $newAttributeModel == 1 ) {
        foreach my $h ( keys(%{$$refHName{"roles"}}) ) {
            my $hSite=$$refHName{"site"}->{$h};
            if ( $hSite eq $site ) {
                my $role=$$refHName{"roles"}->{$h};
                if ( $role =~ /:standby/ ) {
                    $standby++;
                }
            }
        }
    }
    return $standby;
}

sub get_HANA_nodes
{
    my $sid=shift;
    my $site=shift;
    my @nodes;
    if ( $newAttributeModel == 1 ) {
        foreach my $h ( keys(%{$$refHName{"site"}}) ) {
            my $hSite=$$refHName{"site"}->{$h};
            if ( $hSite eq $site ) {
                push (@nodes, $h);
            }
        }
    }
    return @nodes;
}

sub check_node_status
{
    my $sid=shift;
    my $lss=shift;
    my $h=shift;
    if ( $newAttributeModel == 1 ) {
        my $site1=$$refHName{"site"}{$h};
        # my $value=$$refSite{$site1}->{lss};
        if ( $$refSName{"lss"}{$site1} =~ /^[$lss]/ ) {
            return 1;
        }
    } else {
        if ( $$refHName{"roles"}->{$h} =~ /^[$lss]:.:/ ) {
           return 1;
        }
    }
    return 0;
}

sub check_node_mode
{
    my $sid=shift;
    my $mode=shift;
    my $h=shift;
    if ( $newAttributeModel == 1 ) {
        my $site1=$$refHName{"site"}{$h};
        if ( $$refSName{"srr"}{$site1} =~ /^$mode/ ) {
            return 1;
        }
    } else {
        if ( $$refHName{"roles"}->{$h} =~ /[0-9]:$mode:/ ) {
           return 1;
        }
    }
    return 0;
}

sub get_cluster_status
{
    my $return="";
    foreach my $h ( keys(%{$$refHName{"node_state"}} )) {
        my $cl_status;
        if ( ($return eq "") && !($h =~ /^_/) ) {   # TODO: at the moment we filter all strings beginning with "_" maybe thats wrong -> _title, _length
            $cl_status= qx(crmadmin -q -S $h 2>&1);
            if ( !($cl_status =~ /S_NOT_DC/) && ($cl_status =~ /(S_[A-Za-z0-9_-]+)/ )) {
                $return=$1;
            }
        }
    }
    return $return;
}

sub get_number_secondary
{
    my $sid=shift;
    my $lss=shift;
    my $rc=0;
    if ( $newAttributeModel == 1 ) {
        foreach my $s ( keys(%{$$refSName{"srr"}}) ) {
            if ( ( $$refSName{"srr"}->{$s} =~ /S/ ) && ( $$refSName{"lss"}->{$s} =~ /[$lss]/ )) {
               $rc++;
            }
        }
    } else {
        foreach my $h ( keys(%{$$refHName{"roles"}}) ) {
            if ( $$refHName{"roles"}->{$h} =~ /[$lss]:S:/ ) {
               $rc++;
            }
        }
    }
    return $rc;
}

sub get_host_primary
{
    my $sid=shift;
    my $lss=shift;
    my $result="";
    if ( $newAttributeModel == 1 ) {
        foreach my $s ( keys(%{$$refSName{"srr"}}) ) {
            if ( ( $$refSName{"srr"}->{$s} =~ /P/ ) && ( $$refSName{"lss"}->{$s} =~ /[$lss]/ )) {
               $result=$$refSName{"mns"}->{$s};
            }
        }
    } else {
        foreach my $h ( keys(%{$$refHName{"roles"}}) ) {
            if ( $$refHName{"roles"}->{$h} =~ /[$lss]:P:/ ) {
               $result=$h;
            }
        }
    }
    return $result;
}

sub get_host_secondary
{
    my $sid=shift;
    my $lss=shift;
    my $result="";
    if ( $newAttributeModel == 1 ) {
        foreach my $s ( keys(%{$$refSName{"srr"}}) ) {
            if ( ( $$refSName{"srr"}->{$s} =~ /S/ ) && ( $$refSName{"lss"}->{$s} =~ /[$lss]/ )) {
               $result=$$refSName{"mns"}->{$s};
            }
        }
    } else {
        foreach my $h ( keys(%{$$refHName{"roles"}}) ) {
            if ( $$refHName{"roles"}->{$h} =~ /[$lss]:S:/ ) {
               $result=$h;
            }
        }
    }
    return $result;
}

sub get_site_by_host
{
    my $result="";
    my $sid=shift;
    my $h = shift;
# print "get_site_by_host($sid, $h)";
    $result = $$refHName{"site"}->{$h};
    return $result;
}

sub get_lpa_by_host
{
    my $result="";
    my $sid=shift;
    my $h = shift;
# print "get_site_by_host($sid, $h)";
    if ( $newAttributeModel == 1 ) {
        my $site1=$$refHName{"site"}{$h};
        $result = $$refSName{"lpt"}{$site1};
    } else {
        $result = $$refHName{"lpa_${sid}_lpt"}{$h};
    }
    return $result;
}

my $check_lpa_msg="";
my $check_lpa_col="";

sub check_lpa_status
{
    my $sid=shift;
    my $node1=shift;
    my $node2=shift;
    my $lpaGAP="7200"; # TODO: Value must be fetched from the cluster

    my $lpa_node1;
    my $lpa_node2;
    if ( $newAttributeModel == 1 ) {
       my $site1=$$refHName{"site"}{$node1};
       my $site2=$$refHName{"site"}{$node2};
#printf "check_lpa_status: site1=$site1 site2=$site2\n";
       $lpa_node1=$$refSName{"lpt"}{$site1};
       $lpa_node2=$$refSName{"lpt"}{$site2};
    } else {
       $lpa_node1=$$refHName{"lpa_${sid}_lpt"}{$node1};
       $lpa_node2=$$refHName{"lpa_${sid}_lpt"}{$node2};
    }

#printf "check_lpa_status: TEST lpa_node1=$lpa_node1 lpa_node2=$lpa_node2\n";
    my $lpa_delta=abs($lpa_node1 - $lpa_node2);
    my $lpa_wait=($lpaGAP - $lpa_delta);

    if ( (! defined $lpa_node1) || (! defined $lpa_node2)) {
       $check_lpa_msg= "LPA GAP - WAIT because LPA status of one node is missing";
       $check_lpa_col="red";
    } elsif (($lpa_node1<1000) && ($lpa_node2<1000) && ($lpa_node1 != $lpa_node2)) {
       $check_lpa_msg= "Both LPAs in 'special' number range";
       $check_lpa_col="yellow";
    } elsif (($lpa_node1<1000) && ($lpa_node2<1000) && ($lpa_node1 == $lpa_node2)) {
       $check_lpa_msg= "Collision!! Both LPAs in 'special' number range";
       $check_lpa_col="red";
    } elsif (($lpa_node1>1000) && ($lpa_node2>1000) && ($lpa_delta < $lpaGAP)) {
       $check_lpa_msg= "Collision!! LPA GAP - WAIT $lpa_wait seconds";
       $check_lpa_col="red";
    } elsif (($lpa_node1>1000) && ($lpa_node2>1000) && ($lpa_delta >= $lpaGAP)) {
       $check_lpa_msg= "Collision!! LPA GAP PASSED - Check, if AUTOMATIC REGISTRATION is active or register crashed primary manually";
       $check_lpa_col="yellow";
    } else {
       $check_lpa_msg= "LPA: GREEN";
       $check_lpa_col="green";
    }
    return ( $check_lpa_col, $check_lpa_msg);
}

sub check_all_ok
{
    my $sid=shift;
    my $ClusterNodes=shift;
    my $rc=0;
    my $failed="";
    my $result;
    $result=get_nodes_online;
    if ( $result != $ClusterNodes ) {
         $rc++;
         $failed .= " #N=$result";
    }
    $result=get_hana_sync_state($sid);
    # printf "+++ get_hana_sync_state($sid): %s\n", get_hana_sync_state($sid);
    if ( $result ne "SOK" ) {
         $rc++;
         $failed .= " sync=$result ";
    }
    $result=get_number_primary($sid, "34");
    if ( $result != 1 ) {
         $rc++;
         $failed .= " #P=$result ";
    }
    $result=get_number_secondary($sid, "34");
    if ( $result != 1 ) {
         $rc++;
         $failed .= " #S=$result ";
    }
    $result=get_secondary_score($sid);
    if ( $result ne "100" ) {
         $rc++;
         $failed .= " score=$result ";
    }
    $result=get_cluster_status();
    if ( $result ne "S_IDLE" ) {
         $rc++;
         $failed .= " clstatus=$result ";
    }
    return ($rc, $failed);
}

#sub print_attr_host
#{
#	printf "%-22s", "Attribute \\ Host";
#	foreach my $HKey (sort keys %Host) {
#	   printf "%-16s ", $HKey;
#	}
#	printf "\n";
#
#	printf "%s\n", "-" x 120 ;
#
#	foreach my $AKey (sort keys %HName) {
#	   printf "%-22s", $AKey;
#	   foreach my $HKey (sort keys %Host) {
#		   printf "%-16.16s ", $Host{$HKey} -> {$AKey};
#		}
#
#	   printf "\n";
#	}
#	return 0;
#}

sub host_attr2string
{
    my $string="";
    my ($refH, $refN, $title, $sort, $format, $selection) = @_;
    my ($len, $line_len, $hclen);
    #
    # leave function if hash is empty
    #    in this case an empty string is returned
    #
    if ( ! ( keys %$refN )) {
       return "";
    }
    if ( ! defined $format) {
        $format="script"
    }
    if ( $format eq "tables" ) {
        $hclen=max($$refN{_hosts}->{_length}, length($title));
	    $line_len=$hclen+1;
	    $string.=sprintf "%-$hclen.${hclen}s ", "$title";
        #
        # headline
        #
        foreach my $AKey (sort keys %$refN) {
            if ($AKey ne "_hosts") {
                $len = $$refN{$AKey}->{_length};
                $line_len=$line_len+$len+1;

                $string.=sprintf "%-$len.${len}s ", "$$refN{$AKey}->{_title}";
            }
	    }
	    $string.=sprintf "\n";
	    $string.=sprintf "%s\n", "-" x $line_len ;
    }
    #
    # object / name / value lines
    #
    if ( $sort eq "" ) {
        foreach my $HKey (sort keys %$refH) {
            if ( $format eq "tables" ) {
                $string.=sprintf "%-$hclen.${hclen}s ", $HKey;
            }
            foreach my $AKey (sort keys %$refN) {
                if ($AKey ne "_hosts") {
                    $len = max($$refN{$AKey}->{_length}, length($AKey));
                    if ( $format eq "tables" ) {
                        $string.=sprintf "%-$len.${len}s ", $$refH{$HKey} -> {$AKey};
                    } elsif ( $format eq "script" ) {
                        $string.=sprintf "%s/%s/%s=\"%s\"\n", $title, $HKey, $AKey, $$refH{$HKey} -> {$AKey};
                    }
                }
            }
            if ( $format eq "tables" ) {
                $string.=sprintf "\n";
            }
        }
    } else {
        # try to sort by site (other attrs to follow)
        # first try to get a ordered list of attribute values assigned host names
        my $sortVal;
        my %GroupedHosts;
        foreach my $HKey (sort keys %$refH) {
            $sortVal = $$refH{$HKey} -> {$sort};
            push(@{$GroupedHosts{$sortVal}}, $HKey);
        }
        # not ready so far only print the grouped hosts
        foreach my $sortV (sort keys %GroupedHosts) {
            #$StrHosts=join(":", @{$GroupedHosts{$sortV}});
            foreach my $Host (@{$GroupedHosts{$sortV}}) {
                foreach my $AKey (sort keys %$refN) {
                    if ($AKey eq "_hosts") {
                        $len = max($$refN{$AKey}->{_length}, length($title));
                        $string.=sprintf "%-$len.${len}s ", $Host;
                    } else {
                        $len = $$refN{$AKey}->{_length};
                        $string.=sprintf "%-$len.${len}s ", $$refH{$Host} -> {$AKey};
                    }
                }
                $string.=sprintf "\n";
            }
        }
    }
    if ( $format eq "tables" ) {
	    $string.=sprintf "\n";
    }
    return $string;
}

sub print_host_attr
{
    my $string="";
    my ($refH, $refN, $title, $sort, $format, $selection) = @_;
    if ( ! defined $format) {
        $format="script"
    }
    my $print_attributes_result = host_attr2string($refH, $refN, $title, $sort, $format, $selection);
    if ( $print_attributes_result ) {
        printf "%s", $print_attributes_result;
    }
    return 0;
}

sub get_master_nameserver
{
    my @msns;
    foreach my $SKey (sort keys %$refSite) {
        push(@msns, $$refSite{$SKey}->{"mns"});
    }
    return @msns;
}

1;
