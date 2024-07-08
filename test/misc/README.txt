#!/bin/bash
#
# test_kill_secondary (ScaleUp)
# test steps expected
#
# STATUS 10 TEST START
# global             maintenance=<empty>|false  prim=<pSite> secn=<sSite> topology=ScaleUp
# resource  cl_*     maintenance=<empty>|false          
# resource  ms_*     maintenance=<empty>|false          
# site <pSite>: site=pSite lpt=<timestamp> lss=4 srr=P srHook=PRIM srPoll=PRM 
# site <sSite>: site=sSite lpt=30          lss=4 srr=S srHook=SOK  srPoll=SOK
# host <pHost>: clone_state=PROMOTED roles=master1:master:worker:master score=150 site=<pSite> sra=<empty>|- srah=<empty>|- vhost=<pHost> 
# host <sHost>: clone_state=DEMOTED  roles=master1:master:worker:master score=100 site=<sSite> sra=<empty>|- srah=<empty>|- vhost=<sHost> 
#
# ACTION: kill SAP HANA on <sHost>
# Allowed values to change: <sSite>: lpt, lss, srHook, srPoll; <sHost>: clone_state, roles, score
# NEXT STATUS is 20
#
#########################################################################################################################################
#
# STATUS 20 ERROR DETECTED
# global             maintenance=<empty>|false  prim=<pSite> secn=<sSite> topology=ScaleUp
# resource  cl_*     maintenance=<empty>|false          
# resource  ms_*     maintenance=<empty>|false          
# site <pSite>: site=pSite lpt=<timestamp> lss=4   srr=P srHook=PRIM   srPoll=PRM 
# site <sSite>: site=sSite lpt=10          lss=1|2 srr=S srHook=SFAIL  srPoll=SFAIL
# host <pHost>: clone_state=PROMOTED roles=master1:master:worker:master score=150         site=<pSite> sra=<empty>|- srah=<empty>|- vhost=<pHost> 
# host <sHost>: clone_state=DEMOTED  roles=master1::worker:             score=-INFINITY|0 site=<sSite> sra=<empty>|- srah=<empty>|- vhost=<sHost> 
#
# ACTION: wait
# Allowed values to change: <sSite>: srHook, srPoll; <sHost>: clone_state, score
# Sequence/Combiation of lss=4->2->1 and clone_state=DEMOTED->UNDEFINED could be in different order; srPoll might be still in SOK (if monitor was not already running)
# NEXT STATUS is 30
#
#########################################################################################################################################
#
# STATUS 30 BEGIN RECOVER
# global             maintenance=<empty>|false  prim=<pSite> secn=<sSite> topology=ScaleUp
# resource  cl_*     maintenance=<empty>|false          
# resource  ms_*     maintenance=<empty>|false          
# site <pSite>: site=pSite lpt=<timestamp> lss=4   srr=P srHook=PRIM         srPoll=PRM 
# site <sSite>: site=sSite lpt=10          lss=1   srr=S srHook=SFAIL|SWAIT  srPoll=SFAIL
# host <pHost>: clone_state=PROMOTED   roles=master1:master:worker:master score=150         site=<pSite> sra=<empty>|- srah=<empty>|- vhost=<pHost> 
# host <sHost>: clone_state=UNDEFINED  roles=master1::worker:             score=-INFINITY|0 site=<sSite> sra=<empty>|- srah=<empty>|- vhost=<sHost> 
#
# ACTION: wait
# Allowed values to change: <sSite>: lpt, lss, srHook, srPoll; <sHost>: clone_state, roles, score
#
# Expected Cluster Plan: 
# Executing Cluster Transition:
#  * Pseudo action:   ms_SAPHanaCon_HA1_HDB00_stop_0
#  * Resource action: rsc_SAPHanaCon_HA1_HDB00 stop on node02
#  * Pseudo action:   ms_SAPHanaCon_HA1_HDB00_stopped_0
#  * Pseudo action:   ms_SAPHanaCon_HA1_HDB00_start_0
#  * Resource action: rsc_SAPHanaCon_HA1_HDB00 start on node02
#  * Pseudo action:   ms_SAPHanaCon_HA1_HDB00_running_0
#  * Resource action: rsc_SAPHanaCon_HA1_HDB00 monitor=61000 on node02
#
# NEXT STATUS is 40
#
#########################################################################################################################################
#
# STATUS 40 END RECOVER
# <AS STATUS 10>
#
# ACTION: commit test as successful
# Cluster state: S_IDLE
#
########
#
#echo "checkKeyValue() rc=$rc"
#search4getValue 'Hosts/.*/score'
#search4getObject 'Hosts/.*/score="1.0"'

set -u
source ./test-lib


function status_10() { # test status 10 is reached
    # output: all failed tests reported by checkAllKeyValue, nothing more!!
    getAllKeyValue

    patternsPrimarySite=(
        "lss=4"
        "srr=P"
        "lpt=1[6-9]........"
        "srHook=PRIM"
        "srPoll=PRIM"
    ) 

    patternsSecondarySite=(
        "lpt=30"
        "lss=4"
        "srr=S"
        "srHook=SOK"
        "srPoll=SOK"
    )

    patternsPrimaryHost=(
       "clone_state=PROMOTED" 
       "roles=master1:master:worker:master" 
       "score=150" 
       "site=$pSite" 
    )
 
    patternsSecondaryHost=(
       "clone_state=DEMOTED" 
       "roles=master1:master:worker:master" 
       "score=100" 
       "site=$sSite" 
    )
    
    checkAllKeyValue; rc="$?"
    return "$rc"
}

function status_20() { # test status 20 is reached
    # output: all failed tests reported by checkAllKeyValue, nothing more!!
    getAllKeyValue

    patternsPrimarySite=(
        "lss=[12]" 
        "srr=P" 
        "lpt=1[6-9]........" 
        "srHook=(PRIM|SWAIT)" 
        "srPoll=PRIM"
    ) 

    patternsSecondarySite=(
        "lpt=30"
        "lss=4"
        "srr=S"
        "srHook=SOK"
        "srPoll=SOK"
    )

    patternsPrimaryHost=(
       "clone_state=(PROMOTED|DEMOTED)" 
       "roles=master1::worker:" 
       "score=90" 
       "site=$pSite" 
    )
 
    patternsSecondaryHost=(
       "clone_state=DEMOTED" 
       "roles=master1:master:worker:master" 
       "score=100" 
       "site=$sSite" 
    )

    checkAllKeyValue; rc="$?"
    return "$rc"
}

function status_30() { # test status 30 is reached
    # output: all failed tests reported by checkAllKeyValue, nothing more!!
    getAllKeyValue

    patternsPrimarySite=(
        "lpt=(1[6-9]........|30)" 
        "lss=1" 
        "srr=P" 
        "srHook=PRIM" 
        "srPoll=PRIM"
    ) 

    patternsSecondarySite=(
        "lpt=(1[6-9]........|30)" 
        "lss=4"
        "srr=(S|P)"
        "srHook=PRIM"
        "srPoll=SOK"
    )

    patternsPrimaryHost=(
       "clone_state=(UNDEFINED|DEMOTED)" 
       "roles=master1::worker:" 
       "score=90" 
       "site=$pSite" 
    )
 
    patternsSecondaryHost=(
       "clone_state=(DEMOTED|PROMOTED)" 
       "roles=master1:master:worker:master" 
       "score=(100|145)" 
       "site=$sSite" 
       "srah=T"
    )

    checkAllKeyValue; rc="$?"
    return "$rc"
}

function status_40() { # test status 40 is reached
    # output: all failed tests reported by checkAllKeyValue, nothing more!!
    getAllKeyValue

    patternsPrimarySite=(
        "lpt=30"
        "lss=4"
        "srr=S"
        "srHook=SOK"
        "srPoll=SOK"
    ) 

    patternsSecondarySite=(
        "lss=4"
        "srr=P"
        "lpt=1[6-9]........"
        "srHook=PRIM"
        "srPoll=PRIM"
    )

    patternsPrimaryHost=(
       "clone_state=DEMOTED" 
       "roles=master1:master:worker:master" 
       "score=100" 
       "site=$pSite" 
    )
 
    patternsSecondaryHost=(
       "clone_state=PROMOTED" 
       "roles=master1:master:worker:master" 
       "score=150" 
       "site=$sSite" 
    )
    
    checkAllKeyValue; rc="$?"
    return "$rc"
}

function action_10() {
   local sidadm="ha1adm"
   local node="$1"
   local rc=0
   message "HDB kill-9 on node $node"
   timeout 10 ssh "$node" 'su - '"$sidadm"' -c "HDB kill-9" 2>/dev/null 1>/dev/null' rc="$?"
   message "HDB kill-9 on node $node rc=$rc"
   return "$rc"
}

init "$@"

if loopForStatus 10  1; then
   action_10 "$pHost"
   if loopForStatus 20 60 && \
      loopForStatus 30 60 && \
      loopForStatus 40 60 ; then
            message "TEST SUCCESS"
   else
        message "TEST FAILED" 
   fi
else
   message "TEST PREREQUISITES NOT MATCHED"
fi
