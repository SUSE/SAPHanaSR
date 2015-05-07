#
#
# SAPHanaSRTools.pm
# (c) 2014 SUSE Linux Products GmbH
# (c) 2015 SUSE Linux GmbH
# Author: Fabian Herschel
# License: Check if we publish that under GPL v2+
# Version: 0.14.2015.05.07.1
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

use vars qw(@ISA @EXPORT @EXPORT_OK);
@ISA = qw(Exporter);

    # Init immediately so their contents can be used in the 'use vars' below.
    @EXPORT    = qw(max get_nodes_online mysyslog max mysyslog get_nodes_online get_node_status get_sid_and_InstNr get_hana_attributes get_hana_sync_state get_number_primary check_node_status check_node_mode get_number_secondary get_host_primary get_host_secondary check_lpa_status check_all_ok host_attr2string);

#    @EXPORT_OK    = qw(max  mysyslog get_nodes_online);

sub max { 
 # thanks to http://www.perlunity.de/perl/forum/thread_018329.shtml
 my $a = shift;
 my $b = shift;
 return $a > $b ? $a : $b;
}

sub mysyslog ( $$$ ) {
   my ($prio, $form, @param) = ( @_ );
   printf "$form\n", @param;
#   syslog $prio, $form, @param;
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
           if ( defined ($Name{_hosts}->{_length})) {
              $Name{_hosts}->{_length} = max($Name{_hosts}->{_length}, length($host ));
           } else {
              $Name{_hosts}->{_length} = length($host );
           }
           $Name{_hosts}->{_length} = max($Name{_hosts}->{_length}, length( $table_title));
           #
           # now handle the attributes name and value
           #
           $Name{$name}->{$host}=${value};
           if ( defined ($Name{$name}->{_length})) {
              $Name{$name}->{_length} = max($Name{$name}->{_length}, length($value ));
           } else {
              $Name{$name}->{_length} = length($value );
           }
           if ( $name =~ /hana_${sid}_(.*)/ ) {
              $Name{$name}->{_title} =  $1;
           } else {
              $Name{$name}->{_title} = $name; 
           }
           $Name{$name}->{_length} = max($Name{$name}->{_length}, length( $Name{$name}->{_title}));
       }
    }
    close CIB;
    return 0;
}

################
sub get_hana_attributes($)
{
    my $sid = shift;
   undef %Name;
   undef %Host;
open CIB, "cibadmin -Ql |";
while (<CIB>) {
   chomp;
   my ($host, $name, $value);
   my $found=0;
   if ( $_ =~ /nvpair.*name="(\w+_${sid}_\w+)"/ ) {
      $name=$1;
      # find attribute in forever and reboot store :)
      if ( $_ =~ /id="(status|nodes)-([a-zA-Z0-9]+)-/ ) {
         $host=$2;
      }
      if ( $_ =~ /value="([^"]+)"/ ) {
         $value=$1;
         $found=1;
      }
   }
   if ( $found == 1 ) {
       #
       # handle the hosts name and table-title
       #
       $Host{$host}->{$name}=${value};
       if ( defined ($Name{_hosts}->{_length})) {
          $Name{_hosts}->{_length} = max($Name{_hosts}->{_length}, length($host ));
       } else {
          $Name{_hosts}->{_length} = length($host );
       }
       $Name{_hosts}->{_length} = max($Name{_hosts}->{_length}, length( $table_title));
       #
       # now handle the attributes name and value
       #
       $Name{$name}->{$host}=${value};
       if ( defined ($Name{$name}->{_length})) {
          $Name{$name}->{_length} = max($Name{$name}->{_length}, length($value ));
       } else {
          $Name{$name}->{_length} = length($value );
       }
       if ( $name =~ /hana_${sid}_(.*)/ ) {
          $Name{$name}->{_title} =  $1;
       } else {
          $Name{$name}->{_title} = $name;
       }
       $Name{$name}->{_length} = max($Name{$name}->{_length}, length( $Name{$name}->{_title}));
       # printf "%-8s %-20s %-30s\n", $1, $2, $3;
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
    my $h;
    foreach $h ( keys(%{$Name{"hana_${sid}_sync_state"}}) ) {
        if ( $Name{"hana_${sid}_sync_state"}->{$h} =~ /(S.*)/ ) {
           $result=$1;
        }
    }
    return $result;
}

sub get_number_primary($ $)
{
    my $sid=shift;
    my $lss=shift;
    my $rc=0;
    my $h;
    foreach $h ( keys(%{$Name{"hana_${sid}_roles"}}) ) {
        if ( $Name{"hana_${sid}_roles"}->{$h} =~ /[$lss]:P:/ ) {
           $rc++;
        }
    }
    return $rc;
}

sub check_node_status($$$)
{
    my $sid=shift;
    my $lss=shift;
    my $h=shift;
    if ( $Name{"hana_${sid}_roles"}->{$h} =~ /^[$lss]:.:/ ) {
       return 1;
    }
    return 0;
}

sub check_node_mode($$$)
{
    my $sid=shift;
    my $mode=shift;
    my $h=shift;
    if ( $Name{"hana_${sid}_roles"}->{$h} =~ /[0-9]:$mode:/ ) {
       return 1;
    }
    return 0;
}

sub get_number_secondary($ $)
{
    my $sid=shift;
    my $lss=shift;
    my $rc=0;
    my $h;
    foreach $h ( keys(%{$Name{"hana_${sid}_roles"}}) ) {
        if ( $Name{"hana_${sid}_roles"}->{$h} =~ /[$lss]:S:/ ) {
           $rc++;
        }
    }
    return $rc;
}

sub get_host_primary($ $)
{
    my $sid=shift;
    my $lss=shift;
    my $result="";
    my $h;
    foreach $h ( keys(%{$Name{"hana_${sid}_roles"}}) ) {
        if ( $Name{"hana_${sid}_roles"}->{$h} =~ /[$lss]:P:/ ) {
           $result=$h;
        }
    }
    return $result;
}

sub get_host_secondary($ $)
{
    my $sid=shift;
    my $lss=shift;
    my $result="";
    my $h;
    foreach $h ( keys(%{$Name{"hana_${sid}_roles"}}) ) {
        if ( $Name{"hana_${sid}_roles"}->{$h} =~ /[$lss]:S:/ ) {
           $result=$h;
        }
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

    my $lpa_node1=${$Name{"lpa_sle_lpt"}}{$node1};
    my $lpa_node2=${$Name{"lpa_sle_lpt"}}{$node2};

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
    return $check_lpa_col;
}

sub check_all_ok($)
{
    my $sid=shift;
    my $rc=0;
    my $failed="";
    my $result;
    $result=get_nodes_online;
    if ( $result != 2 ) {
         $rc++;  
         $failed .= " #N=$result"; 
    }
    $result=get_hana_sync_state($sid);
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
    $hclen=$Name{_hosts}->{_length};
    $line_len=$hclen+1;
    $string .= sprintf "%-$hclen.${hclen}s ", "$table_title";
    foreach $AKey (sort keys %Name) {
      if ($AKey ne "_hosts") {
         $len = $Name{$AKey}->{_length};
         $line_len=$line_len+$len+1;
         $string .= sprintf "%-$len.${len}s ", $Name{$AKey}->{_title};
       }
    }
        $string .= sprintf "\n";
        $string .= sprintf "%s\n", "-" x $line_len ;
        foreach $HKey (sort keys %Host) {
           $string .= sprintf "%-$hclen.${hclen}s ", $HKey;
           foreach $AKey (sort keys %Name) {
           if ($AKey ne "_hosts") {
               $len = $Name{$AKey}->{_length};
               $string .= sprintf "%-$len.${len}s ", $Host{$HKey} -> {$AKey};
            }
        }
           $string .= sprintf "\n";
        }
        return $string;
}

#
################ END CUT - MOVE THAT TO AN PERL-LIBRARY LATER
#

1;
