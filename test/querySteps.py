import sys, json; 

data=json.load(sys.stdin); 

def slashIt(area, object, key, val):
    print('{}/{}/{}="{}"'.format(area, object, key, val))
    return 0

def loopCondition(conditions, area, object, key):
    for cond in conditions:
        slashIt(area, object, key, cond)
    return 0;

testID= data['test'];
testName= data['name'];
steps=data['steps']; 
start=data['start'];

slashIt("Tests",testID,"name",testName)
slashIt("Tests",testID,"start",start)

for step in data['steps']:
    try:
        stepID=step['step']
        stepName=step['name']
        stepNext=step['next']
        stepLoop=step['loop']
        stepIntv=step['wait']
    except:
        print("step {} missing definitions".format(stepID))
    try:
        stepPost=step['post']
    except:
        stepPost=""
    slashIt("Steps",testID+"-"+stepID, "name", stepName)
    slashIt("Steps",testID+"-"+stepID, "next", stepNext)
    slashIt("Steps",testID+"-"+stepID, "loop", stepLoop)
    slashIt("Steps",testID+"-"+stepID, "wait", stepIntv)
    slashIt("Steps",testID+"-"+stepID, "post", stepPost)
    try:
        pSite=step['pSite']
        loopCondition(pSite,"Steps",testID+"-"+stepID,"pSite")
    except:
        print("test {} is missing pSite definition".format(stepID)) 
    try:
        sSite=step['sSite']
        loopCondition(sSite,"Steps",testID+"-"+stepID,"sSite")
    except:
        print("test {} is missing sSite definition".format(stepID)) 
    try:
        pHost=step['pHost']
        loopCondition(pHost,"Steps",testID+"-"+stepID,"pHost")
    except:
        print("test {} is missing pHost definition".format(stepID)) 
    try:
        sHost=step['sHost']
        loopCondition(sHost,"Steps",testID+"-"+stepID,"sHost")
    except:
        print("test {} is missing sHost definition".format(stepID)) 
    
