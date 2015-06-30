#
#
# SAPHanaSRTools.pm
# (c) 2014 SUSE Linux Products GmbH
# (c) 2015 SUSE Linux GmbH
# Author: Fabian Herschel
# License: Check if we publish that under GPL v2+
# Version: 0.16.2015.06.29.1
#
##################################################################

package SAPHanaSRTools;
require Exporter;
use POSIX;
# TODO: PRIO2: Get it stric again 
#use strict;
use Sys::Syslog;
use Sys::Hostname;
use File::Path;
use Switch;

my $VERSION="1.0";
my $newAttributeModel=0;

use vars qw(@ISA @EXPORT @EXPORT_OK);
@ISA = qw(Exporter);

    # Init immediately so their contents can be used in the 'use vars' below.
    @EXPORT    = qw(max get_nodes_online mysyslog max mysyslog get_nodes_online get_node_status get_sid_and_InstNr get_hana_attributes get_hana_sync_state get_number_primary check_node_status check_node_mode get_number_secondary get_host_primary get_host_secondary check_lpa_status check_all_ok host_attr2string get_lpa_by_host get_site_by_host print_attr_host print_host_attr set_new_attribute_model get_new_attribute_model get_number_HANA_standby get_HANA_nodes get_node_list);

#    @EXPORT_OK    = qw(max  mysyslog get_nodes_online);

sub set_new_attribute_model()
{
    $newAttributeModel=1;
}

sub get_new_attribute_model()
{
    return $newAttributeModel;
}

sub max { 
 # thanks to http://www.perlunity.de/perl/forum/thread_018329.shtml
 my $a = shift;
 my $b = shift;
 return $a > $b ? $a : $b;
}

sub mysyslog ( $$$ ) {
   my ($prio, $form, @param) = ( @_ );
   syslog $prio, $form, @param;
}

sub get_nodes_online 
{
    my $rc=0;
    my $match="Ok:\s+([0-9])\s+nodes online";
    my $match="Ok:\s+([0-9]+)\s+nodes? online";
    my $match="Ok: ([0-9]+) ";
    open crm, "crm_mon -s |";
    while (<crm>) {
        if (/$match/) {
           $rc=$1
        }
    }
    close crm;
    return $rc;
}

sub get_node_status($)
{
    # typically returns online, standby or offline
    my $result="offline";
    my $node=shift;
    open crm, "crm_mon -1 |";
    #- case one offline/standby and one online
    # Node fscs99: OFFLINE (standby)
    # Online: [ fscs98 ]
    #- case both standby
    # Node fscs99: standby
    # Node fscs98: standby
    #- case one standby one online
    # Node fscs99: standby
    # Online: [ fscs98 ]
    #- case both online
    # Online: [ fscs98 fscs99 ]
    while (<crm>) {
        if ( /^Online:.*\s$node\s/ ) {
           #printf("O: %s\n", $_);
           $result="online";
        } elsif ( /^Node\s+$node:\s+(\S+)/  ) {
           #printf("N: %s: %s\n", $_, $1);
           $result=tolower($1);

        }
    }
    close crm;
    return $result;
}

sub get_node_list()
{
    # crm_node -l | awk '$3 == "member" { if ($2 != me) { print $2 }}'
    my @nodes;
    open crm, "crm_node -l |";
    while (<crm>) {
        if ( /\S+\s+(\S+)\s+member$/ ) {
            push (@nodes, $1);
        }
    }
    close crm;
    return @nodes;
}

#
# works only, if ONE SAPinstance (here HANA) is installed on the cluster
#
sub get_sid_and_InstNr()
{
    my $sid=""; my $Inr=""; my $noDAACount = 0; my $gotAnswer = 0;
    open ListInstances, "/usr/sap/hostctrl/exe/saphostctrl -function ListInstances|";
    while (<ListInstances>) {
        # try to catch:  Inst Info : LNX - 42 - lv9041 - 740, patch 36, changelist 1444691
        chomp;
        if ( /^[^:]+:\s*(\w+)\s*-\s*(\w+)\s*-/ ) {
            $gotAnswer = 1;
            my $foundSID=$1;
            my $foundINO=$2;
            if ( $foundSID ne "DAA" ) {
                $noDAACount++;
                $sid=tolower($foundSID);
                $Inr=$foundINO;
            }
        }
#       if ( $_ =~ /:\s+([A-Z][A-Z0-9][A-Z0-9])\s+-\s+([0-9][0-9])/ ) {
#          $sid=tolower("$1");
#          $Inr=$2;
    }
    close ListInstances;
    #printf (" get_sid_and_InstNr: return (%s)\n", join(",", ( $sid, $Inr, $noDAACount, $gotAnswer )));
    return ( $sid, $Inr, $noDAACount, $gotAnswer );
}

my $table_title = "Host \\ Attr";
sub OLDget_hana_attributes($)
{
    my $sid = shift;
    open CIB, "cibadmin -Ql |";
    while (<CIB>) {
       chomp;
       if ( $_ =~ /nvpair\s+id="status-([a-zA-Z0-9]+)-\w+"\s+name="(\w+_${sid}_\w+)"\s+value="([^"]+)"/ ) {
           my ($host, $name, $value) = ( $1, $2, $3 );
           #
           # handle the hosts name and table-title
           #
           $Host{$host}->{$name}=${value};
           if ( defined ($HName{_hosts}->{_length})) {
              $HName{_hosts}->{_length} = max($HName{_hosts}->{_length}, length($host ));
           } else {
              $HName{_hosts}->{_length} = length($host );
           }
           $HName{_hosts}->{_length} = max($HName{_hosts}->{_length}, length( $table_title));
           #
           # now handle the attributes name and value
           #
           $HName{$name}->{$host}=${value};
           if ( defined ($HName{$name}->{_length})) {
              $HName{$name}->{_length} = max($HName{$name}->{_length}, length($value ));
           } else {
              $HName{$name}->{_length} = length($value );
           }
           if ( $name =~ /hana_${sid}_(.*)/ ) {
              $HName{$name}->{_title} =  $1;
           } else {
              $HName{$name}->{_title} = $name; 
           }
           $HName{$name}->{_length} = max($HName{$name}->{_length}, length( $HName{$name}->{_title}));
       }
    }
    close CIB;
    return 0;
}

sub insertAttribute($$$$$$) { 
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
sub get_hana_attributes($)
{
    my $sid = shift;
open CIB, "cibadmin -Ql |";
while (<CIB>) {
   chomp;
   my ($host, $name, $site, $value);
   if ( $_ =~ /nvpair.*name="([a-zA-Z0-9\_\-]+_${sid}_([a-zA-Z0-9\-\_]+))"/ ) {
      $name=$1;
      if ( $_ =~ /id=.(status|nodes)-([a-zA-Z0-9\_\-]+)-/ ) {
         # found attribute in nodes forever and reboot store
         $host=$2;
         if ( $_ =~ /value="([^"]+)"/ ) {
             $value=$1;
#printf "insert $sid HOST $host $name $value\n";
             insertAttribute($sid, \%Host, \%HName, $host, $name, $value);
         }
      } elsif ( $_ =~ /id=.SAPHanaSR-[a-zA-Z0-9\_\-]+_site_[a-zA-Z0-9\-]+_([a-zA-Z0-9\_\-]+)/) {
         # found a site attribute
         $site=$1;
         if ( $name =~ /[a-zA-Z0-9\_\-]+_site_([a-zA-Z0-9\-]+)/ ) {
            $name = $1;
         }
         if ( $_ =~ /value="([^"]+)"/ ) {
             $value=$1;
#printf "insert $sid SITE $site $name $value\n";
             insertAttribute($sid, \%Site, \%SName, $site, $name, $value);
         }
      } elsif ( $_ =~ /id=.SAPHanaSR-[a-zA-Z0-9\_\-]+_glob_[a-zA-Z0-9\_\-]+/) {
         # found a global attribute
         $host="GLOBAL";
         if ( $name =~ /([a-zA-Z0-9\_\-]+)_glob_([a-zA-Z0-9\_\-]+)/ ) {
            $name = $2;
         }
         if ( $_ =~ /value="([^"]+)"/ ) {
             $value=$1;
#printf "insert $sid GLOB global $name $value\n";
             insertAttribute($sid, \%Global, \%GName, "global", $name, $value);
         }
      }
   }

}
close CIB;
    return 0;
}

################

sub get_hana_sync_state($)
{
    my $sid=shift;
    my $result="";
    if ( $newAttributeModel == 1 ) {    
        $result = $GName{sync_state}->{"global"};
    } else  {
        my $h;
        foreach $h ( keys(%{$HName{sync_state}}) ) {
            if ( $HName{sync_state}->{$h} =~ /(S.*)/ ) {
               $result=$1;
            }
        }
    }
    return $result;
}

sub get_number_primary($ $)
{
    my $sid=shift;
    my $lss=shift;
    my $rc=0;
    if ( $newAttributeModel == 1 ) {    
        my $s;
        foreach $s ( keys(%{$SName{"srr"}}) ) {
            if ( ( $SName{"srr"}->{$s} =~ /P/ ) && ( $SName{"lss"}->{$s} =~ /[$lss]/ )) {
               $rc++;
            }
        }
    } else  {
        my $h;
        foreach $h ( keys(%{$HName{"roles"}}) ) {
            if ( $HName{"roles"}->{$h} =~ /[$lss]:P:/ ) {
               $rc++;
            }
        }
    }
    return $rc;
}

sub get_number_HANA_standby($$)
{
    my $sid=shift;
    my $site=shift;
    my $standby=0;
    if ( $newAttributeModel == 1 ) {
        my $h;
        foreach $h ( keys(%{$HName{"roles"}}) ) {
            my $hSite=$HName{"site"}->{$h};
            if ( $hSite eq $site ) {
                my $role=$HName{"roles"}->{$h};
                if ( $role =~ /:standby/ ) {
                    $standby++;
                }
            }
        }
    }
    return $standby;
}

sub get_HANA_nodes($$)
{
    my $sid=shift;
    my $site=shift;
    my @nodes;
    if ( $newAttributeModel == 1 ) {
        my $h;
        foreach $h ( keys(%{$HName{"site"}}) ) {
            my $hSite=$HName{"site"}->{$h};
            if ( $hSite eq $site ) {
                push (@nodes, $h);
            }
        } 
    }
    return @nodes;
}

sub check_node_status($$$)
{
    my $sid=shift;
    my $lss=shift;
    my $h=shift;
    if ( $newAttributeModel == 1 ) {    
        my $site1=${$HName{"site"}}{$h};
        if ( ${$SName{"lss"}}{$site1} =~ /^[$lss]/ ) {
            return 1
        }
    } else {
        if ( $HName{"roles"}->{$h} =~ /^[$lss]:.:/ ) {
           return 1;
        }
    }
    return 0;
}

sub check_node_mode($$$)
{
    my $sid=shift;
    my $mode=shift;
    my $h=shift;
    if ( $newAttributeModel == 1 ) {    
        my $site1=${$HName{"site"}}{$h};
        if ( ${$SName{"srr"}}{$site1} =~ /^$srr/ ) {
            return 1
        }
    } else {
        if ( $HName{"roles"}->{$h} =~ /[0-9]:$mode:/ ) {
           return 1;
        }
    }
    return 0;
}

sub get_number_secondary($ $)
{
    my $sid=shift;
    my $lss=shift;
    my $rc=0;
    if ( $newAttributeModel == 1 ) {    
        my $s;
        foreach $s ( keys(%{$SName{"srr"}}) ) {
            if ( ( $SName{"srr"}->{$s} =~ /S/ ) && ( $SName{"lss"}->{$s} =~ /[$lss]/ )) {
               $rc++;
            }
        }
    } else {
        my $h;
        foreach $h ( keys(%{$HName{"roles"}}) ) {
            if ( $HName{"roles"}->{$h} =~ /[$lss]:S:/ ) {
               $rc++;
            }
        }
    }
    return $rc;
}

sub get_host_primary($ $)
{
    my $sid=shift;
    my $lss=shift;
    my $result="";
    if ( $newAttributeModel == 1 ) {    
        my $s;
        foreach $s ( keys(%{$SName{"srr"}}) ) {
            if ( ( $SName{"srr"}->{$s} =~ /P/ ) && ( $SName{"lss"}->{$s} =~ /[$lss]/ )) {
               $result=$SName{"mns"}->{$s};
            }
        }
    } else {
        my $h;
        foreach $h ( keys(%{$HName{"roles"}}) ) {
            if ( $HName{"roles"}->{$h} =~ /[$lss]:P:/ ) {
               $result=$h;
            }
        }
    }
    return $result;
}

sub get_host_secondary($ $)
{
    my $sid=shift;
    my $lss=shift;
    my $result="";
    if ( $newAttributeModel == 1 ) {    
        my $s;
        foreach $s ( keys(%{$SName{"srr"}}) ) {
            if ( ( $SName{"srr"}->{$s} =~ /S/ ) && ( $SName{"lss"}->{$s} =~ /[$lss]/ )) {
               $result=$SName{"mns"}->{$s};
            }
        }
    } else {
        my $h;
        foreach $h ( keys(%{$HName{"roles"}}) ) {
            if ( $HName{"roles"}->{$h} =~ /[$lss]:S:/ ) {
               $result=$h;
            }
        }
    }
    return $result;
}

sub get_site_by_host($ $)
{
    my $result="";
    my $sid=shift;
    my $h = shift;
# print "get_site_by_host($sid, $h)";
    $result = $HName{"site"}->{$h};
    $result = $Host{$h}->{"site"};
    return $result;
}

sub get_lpa_by_host($$)
{
    my $result="";
    my $sid=shift;
    my $h = shift;
# print "get_site_by_host($sid, $h)";
    if ( $newAttributeModel == 1 ) {
        my $site1=${$HName{"site"}}{$h};
        $result = ${$SName{"lpt"}}{$site1};
    } else {
        $result = ${$HName{"lpa_${sid}_lpt"}}{$h};
    }
    return $result;
}

my $check_lpa_msg="";
my $check_lpa_col="";

sub check_lpa_status($$$)
{
    my $sid=shift;
    my $node1=shift;
    my $node2=shift;
    my $lpaGAP="7200"; # TODO: Value must be fetched from the cluster

    my $lpa_node1;
    my $lpa_node2;
    if ( $newAttributeModel == 1 ) {
       my $site1=${$HName{"site"}}{$node1};
       my $site2=${$HName{"site"}}{$node2};
#printf "check_lpa_status: site1=$site1 site2=$site2\n";
       $lpa_node1=${$SName{"lpt"}}{$site1};
       $lpa_node2=${$SName{"lpt"}}{$site2};
    } else {
       $lpa_node1=${$HName{"lpa_${sid}_lpt"}}{$node1};
       $lpa_node2=${$HName{"lpa_${sid}_lpt"}}{$node2};
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

sub check_all_ok($$)
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
#printf "get_hana_sync_state($sid): %s\n", get_hana_sync_state($sid);
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
    return ($rc, $failed);
}

sub host_attr2string()
{
    my $string;
    my ($AKey, $HKey, $len, $line_len, $hclen);
    $hclen=$HName{_hosts}->{_length};
    $line_len=$hclen+1;
    $string .= sprintf "%-$hclen.${hclen}s ", "$table_title";
    foreach $AKey (sort keys %HName) {
      if ($AKey ne "_hosts") {
         $len = $HName{$AKey}->{_length};
         $line_len=$line_len+$len+1;
         $string .= sprintf "%-$len.${len}s ", $HName{$AKey}->{_title};
       }
    }
        $string .= sprintf "\n";
        $string .= sprintf "%s\n", "-" x $line_len ;
        foreach $HKey (sort keys %Host) {
           $string .= sprintf "%-$hclen.${hclen}s ", $HKey;
           foreach $AKey (sort keys %HName) {
           if ($AKey ne "_hosts") {
               $len = $HName{$AKey}->{_length};
               $string .= sprintf "%-$len.${len}s ", $Host{$HKey} -> {$AKey};
            }
        }
           $string .= sprintf "\n";
        }
        return $string;
}

sub print_attr_host()
{
    my ($HKey, $AKey);
	printf "%-22s", "Attribute \\ Host";
	foreach $HKey (sort keys %Host) {
	   printf "%-16s ", $HKey;
	}
	printf "\n";

	printf "%s\n", "-" x 120 ;

	foreach $AKey (sort keys %HName) {
	   printf "%-22s", $AKey;
	   foreach $HKey (sort keys %Host) {
		   printf "%-16.16s ", $Host{$HKey} -> {$AKey};
		}

	   printf "\n";
	}
	return 0;
}

sub print_host_attr()
{
    my ($AKey, $HKey, $len, $line_len, $hclen);
    $hclen=$HName{_hosts}->{_length};
    $line_len=$hclen+1;
	printf "%-$hclen.${hclen}s ", "$table_title";
	foreach $AKey (sort keys %HName) {
       if ($AKey ne "_hosts") {
           $len = $HName{$AKey}->{_length};
           $line_len=$line_len+$len+1;
           printf "%-$len.${len}s ", $HName{$AKey}->{_title};
       }
	}
	printf "\n";
	printf "%s\n", "-" x $line_len ;
	foreach $HKey (sort keys %Host) {
	   printf "%-$hclen.${hclen}s ", $HKey;
	   foreach $AKey (sort keys %HName) {
           if ($AKey ne "_hosts") {
               $len = $HName{$AKey}->{_length};
               printf "%-$len.${len}s ", $Host{$HKey} -> {$AKey};
            }
        }
	   printf "\n";
	}
	return 0;
}
#
################ END CUT - MOVE THAT TO AN PERL-LIBRARY LATER
#

1;
