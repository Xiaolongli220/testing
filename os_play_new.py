import os
import subprocess
import datetime
import re
# from ats import aetest
import shutil
import sys
import shlex
from pathlib import Path
from multiprocessing import Process
import time
import argparse
from pprint import pprint,pformat

test_path = (os.path.dirname(os.path.abspath(__file__)))
sys.path.append(test_path + '/utils')

import utils

IMAGE_DEST = "latest_csr"
JOBS_SUPPORTED = ["xsanity", "route", "pdp", "lb", "neg", "misc", "history",
                  "b2b", "sanity", "spl", "hp", "pi25regression", "pi25sanity",
                  "precommitsanity", "idc","mhop","pd_idc_mhop","dca","dca2",
                  "site_manager",'teacat']
JOBS_TCL_REGRESSION = ["xsanity", "route", "pdp", "lb", "neg", "misc", "history", "b2b"]
JOBS_PYATS_REGRESSION = ["spl", "hp","idc","mhop","pd_idc_mhop","pfr_DCA",
                         "dca","dca2","site_manager",'teacat']
JOBS_TCL_SANITY = ["sanity", "pi25sanity"]
JOBS_PYATS_SANITY = [""]
servername = "10.74.28.11"

def get_images(hub, transit_hub, branch1, branch2):
    hub_image = ""
    transit_hub_image = ""
    branch1_image = ""
    branch2_image = ""
    hub[:-4]+"_"+transit_hub[:-4]+"_"+branch1[:-4]+"_"+branch2[:-4]
    if "throttle" in hub.lower() and not os.path.isfile(hub):
        hub_image = os.path.join(IMAGE_DEST, get_image_name(hub))
    else:
        hub_image = os.path.join(IMAGE_DEST, os.path.basename(hub))
    if "throttle" in transit_hub.lower() and not os.path.isfile(transit_hub):
        transit_hub_image = os.path.join(IMAGE_DEST, get_image_name(transit_hub))
    else:
        transit_hub_image = os.path.join(IMAGE_DEST, os.path.basename(transit_hub))
    if "throttle" in branch1.lower() and not os.path.isfile(branch1):
        branch1_image = os.path.join(IMAGE_DEST, get_image_name(branch1))
    else:
        branch1_image = os.path.join(IMAGE_DEST, os.path.basename(branch1))
    if "throttle" in branch2.lower() and not os.path.isfile(branch2):
        branch2_image = os.path.join(IMAGE_DEST, get_image_name(branch2))
    else:
        branch2_image = os.path.join(IMAGE_DEST, os.path.basename(branch2))
    return (hub_image, transit_hub_image, branch1_image, branch2_image) 
   
 
def get_image_name(branch):
    # GREP image directory
    proc = subprocess.Popen(['ls', IMAGE_DEST], stdout=subprocess.PIPE)
    tmp = proc.stdout.read().decode("utf-8")
    image_ls = []
    image_ls = tmp.splitlines()
    image = ""

    for element in image_ls:
        test_image = element.lower()
        if "csr1000v" in test_image and "ova" in test_image and branch in test_image and utils.get_label(branch).lower() in test_image:
            # Copy the image
            image = element
            break
    print("Get image name is: "+image)
    return image


#def get_branch_combination(hub, transit_hub, branch1, branch2):
#    return hub.replace("throttle","")+"_"+transit_hub.replace("throttle","")+"_"+branch1.replace("throttle","")+"_"+branch2.replace("throttle","")

#def get_branch_label(hub_image, transit_hub_image, branch1_image, branch2_image):
#    label = ""
#    branches_set = set((hub_image, transit_hub_image, branch1_image, branch2_image))
#    for branch in branches_set:
#        label += "_" + branch.replace("-","").replace("csr","").replace("1000v","").replace(".ova","").replace("universalk9","").replace(".","").replace("latest_csr","").replace("/","")
#    return label

def execute_virtual_test_harness(job_type,
                                 logs_dir,
                                 mail,
                                 test_framework,
                                 input_configuration,
                                 pi25,
                                 unique_id,
                                 deleteTopology,
                                 topology_name,
                                 hub_image,
                                 transit_hub_image,
                                 branch1_image,
                                 branch2_image,
                                 tbCreateFlag,
								 job_params):
    print(topology_name)
    script_command = ""
    virtual_testbed_bringup = ""
    if job_type == "csr":
        virtual_testbed_bringup = "virtual_testbed_bringup.py"
    elif test_framework == "tcl":
        virtual_testbed_bringup = "virtual_testbed_tcl_bringup.py"
    elif test_framework == "pyats":
        virtual_testbed_bringup = "virtual_testbed_pyats_bringup.py"
    elif test_framework == "pyats_virl":
        virtual_testbed_bringup = "virtual_testbed_pyats_bringup_using_virl.py"
    else:
        print("ERROR: Unsupported test framework")
        sys.exit(1)
#    if logs_dir:
    if test_framework == "pyats_virl":
          script_command = "python %s -s %s -u 'cisco' -p 'cisco' -m 'p4p2' -d '/storage/users/dich/tcl_script/PI_pfrv3/virl/%s' --isPhysical False --input_configuration '%s' --topology_name '%s' --job_type '%s' --pi25 '%s' -ui '%s' --deleteTopology '%s' -hub_image '%s' -transit_hub_image '%s' -branch1_image '%s' -branch2_image '%s ' -tbCreateFlag '%s' -job_params '%s' -mail '%s'" \
        % (virtual_testbed_bringup,
           servername,
           topology_name,
           input_configuration,
           topology_name,
           job_type,
           pi25,
           unique_id,
           deleteTopology,
           hub_image,
           transit_hub_image,
           branch1_image,
           branch2_image,
           tbCreateFlag,
           job_params,
           mail)
    else:
        script_command = "python %s -s %s -u 'cisco' -p 'cisco' -m 'p4p2' -d '/storage/users/dich/tcl_script/PI_pfrv3/virl/%s' --isPhysical False --input_configuration '%s' --topology_name '%s' --job_type '%s' --pi25 '%s' -ui '%s' --deleteTopology '%s' -hub_image '%s' -transit_hub_image '%s' -branch1_image '%s' -branch2_image '%s' -job_params '%s' " \
        % (virtual_testbed_bringup,
           servername,
           topology_name,
           input_configuration,
           topology_name,
           job_type,
           pi25,
           unique_id,
           deleteTopology,
           hub_image,
           transit_hub_image,
           branch1_image,
           branch2_image,
           job_params)

    print("script_cmd: %s" % script_command)

    print('process id:', os.getpid())
    print('parent process id:', os.getppid())
    #import pdb;pdb.set_trace()
    print("Executing virtual test harness %s\n\n" % script_command)
    #my_env = os.environ.copy()
    #print(pformat(my_env))

    #time.sleep(10)
    ret_code = subprocess.call(shlex.split(script_command))
    if ret_code <0:
        print("ERROR: return code of calling virtual_testbed_bringup :" + str(ret_code) )
    else:
        print("PASS: return code of calling virtual_testbed_bringup :" + str(ret_code))


    # for i in range(3):
    #     ret_code = subprocess.call(shlex.split(script_command))
    #     if ret_code <0:
    #         print("ERROR: return code of calling virtual_testbed_bringup :" + str(ret_code) + " sleep 10s and recall again")
    #         time.sleep(10)
    #     else:
    #         print("PASS: return code of calling virtual_testbed_bringup :" + str(ret_code))
    #         break
    return ret_code

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--private", help="Set to true if using private image", required=False)
    parser.add_argument("-m", "--mail", help="Mail recipient", required=False)
    parser.add_argument("-j", "--job_type", help="Type of the job to run", required=False)
    parser.add_argument("-a", "--archive", help="Archive results in remote fileserver", required=False)
    parser.add_argument("-tf", "--test_framework", help="Test framework used", required=False)
    parser.add_argument("-ic", "--input_configuration", help="Input configuration to be used", required=False)
    parser.add_argument("-pi", "--pi25", help="Set to true for pi25, else false", required=False)
    parser.add_argument("-ui", "--unique_id", help="Unique id for the test", required=False)
    parser.add_argument("-deleteTopology", "--deleteTopology",
                            help="[required] Set it to True is the testbed be deleted after running the scripts, else False",
                            required=False, default=True)
    parser.add_argument("-hb", "--hub", help="Name of the branch to pick up latest image for hub", required=False)
    parser.add_argument("-thb", "--transit_hub", help="Name of the branch to pick up latest image for transit hub", required=False)
    parser.add_argument("-b1", "--branch1", help="Name of the branch to pick up latest image for branch1", required=False)
    parser.add_argument("-b2", "--branch2", help="Name of the branch to pick up latest image for branch2", required=False)
    parser.add_argument("-tbCreateFlag", "--tbCreateFlag", help="[Not required] create vmlcoud testbed", required=False,default=True)
    parser.add_argument("-job_params", "--job_params", help="[Not required] job_params", required=False,default='')
    parser.add_argument("-unique_testbed", "--unique_testbed", help="[Not required] unique_testbed", required=False,default=False)
    args = parser.parse_args()
    private = args.private
    mail = args.mail
    job_type = args.job_type.lower()
    archive = args.archive
    test_framework = args.test_framework.lower()
    input_configuration = os.path.join("configuration", args.input_configuration)
    pi25 = args.pi25
    unique_id = args.unique_id.lower()
    deleteTopology = args.deleteTopology
    hub = args.hub
    transit_hub = args.transit_hub
    branch1 = args.branch1
    branch2 = args.branch2
    tbCreateFlag=args.tbCreateFlag
    job_params=args.job_params
    unique_testbed=args.unique_testbed
    # Locate N-1 day's image
    format = "%Y%m%d"
    today = datetime.datetime.today() - datetime.timedelta(1)
    s = today.strftime(format)
   
    # Get image name
    #qiangwa change
#    (hub_image, transit_hub_image, branch1_image, branch2_image, branch_combination, label) = ("", "", "", "", "", "")
#    (hub_image, transit_hub_image, branch1_image, branch2_image) = get_images(hub, transit_hub, branch1, branch2)
#    branch_combination = utils.get_branch_combination(hub, transit_hub, branch1, branch2)
#    label = utils.get_branch_label(hub_image, transit_hub_image, branch1_image, branch2_image)
    (hub_image, transit_hub_image, branch1_image, branch2_image, branch_combination, label) = (hub, transit_hub, branch1, branch2, "custom_combi", "166")    
    logs_dir = "" 
    if archive == "true":
        logs_dir = branch_combination

    #os.chdir("/ws/krannara-sjc/iwan2x/test_harness_interop")
    job_log_dir = "/storage/users/dich/tcl_script/PI_pfrv3/logs"
    topology_name = ""
    jobs_to_run = []
    processes_running = []
    print("jialpeng:debug os_play_new.py")
    if job_type == "csr":
        if private == "true":
            topology_name = unique_id+"_"+mail+"_"+job_type
        else:
            topology_name = unique_id+"_"+mail+"_"+job_type+"_"+label
        #qiangwa modi
#        j = Process(target=execute_virtual_test_harness, name=topology_name, args=(job_type, job_log_dir, test_framework, input_configuration, pi25, unique_id, deleteTopology, topology_name, hub_image, transit_hub_image, branch1_image, branch2_image,))

#        j.start()
#        j.join()
        execute_virtual_test_harness(job_type,
                                     job_log_dir,
                                     test_framework,
                                     input_configuration,
                                     pi25,
                                     unique_id,
                                     deleteTopology,
                                     topology_name,
                                     hub_image,
                                     transit_hub_image,
                                     branch1_image,
                                     branch2_image)
    else:
        if job_type == "regression":
            if test_framework == "tcl":
                jobs_to_run = JOBS_TCL_REGRESSION[:]
            elif test_framework == "pyats":
                jobs_to_run = JOBS_PYATS_REGRESSION[:]
            else:
                print("ERROR: Unsupported test framework")
                sys.exit(1)
        elif job_type == "precommitsanity":
            if test_framework == "tcl":
                jobs_to_run = JOBS_TCL_SANITY[:]
            elif test_framework == "pyats":
                jobs_to_run = JOBS_PYATS_SANITY[:]
            else:
                print("ERROR: Unsupported test framework")
                sys.exit(1)
        else:
            if job_type in JOBS_SUPPORTED:
                jobs_to_run.append(job_type)    
        for job in jobs_to_run:
            if private == "true":
                topology_name = unique_id+"_"+mail+"_"+job
            else:
                topology_name = unique_id+"_"+mail+"_"+job+"_"+label
            ##Add if logic to create only one testbed instance to run the job. if one exists, it will delete the old one
            if unique_testbed == "true":
                topology_name = unique_id+"_"+job
            if archive == "true":
                job_log_dir = os.path.join(logs_dir, job)
            if job_type == "precommitsanity" and job == "sanity":
                input_configuration = os.path.join("configuration", "pfr_mdc_27.yaml")
            elif job_type == "precommitsanity" and job == "pi25sanity":
                input_configuration = os.path.join("configuration", "pfr_mdc_25.yaml")

                
            print("===============Step: Run with %s===============" %execute_virtual_test_harness)

            j = Process(target=execute_virtual_test_harness, name=topology_name, args=(job, job_log_dir,mail, test_framework, input_configuration, pi25, unique_id, deleteTopology, topology_name, hub_image, transit_hub_image, branch1_image, branch2_image,tbCreateFlag,job_params))
            j.start()
            processes_running.append(j)
            print("sleep 120s\n")
            time.sleep(120)
    
        for el in processes_running:
            el.join()
     
        print("Waiting for the jobs to finish")

# shaujosh
#print("os_play is exiting with code:", ret_code)
#sys.exit(ret_code)
