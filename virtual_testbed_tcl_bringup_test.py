import argparse
from ats import aetest
from ats import tcl
from ats import topology
from ats.atslog.utils import banner
from csccon import *
from csccon import get_csccon_default_array
from csccon import set_csccon_default
from ats.topology import Testbed, Device, Interface
from ats.topology import loader
import yaml, os, sys, getopt, logging, time, shlex, subprocess, signal, re
from collections import OrderedDict
from unicon.eal.dialogs import Statement, Dialog
from ats.atslog.utils import banner
from ats import tcl
from ats import topology
from ats.atslog.utils import banner
from csccon import *
from csccon.exceptions import InvalidCliError
import pysftp
import shutil
import datetime
import getpass
import argparse



test_path = (os.path.dirname(os.path.abspath(__file__)))
sys.path.append(test_path + '/smart_license')
sys.path.append(test_path + '/netmap2yaml')
sys.path.append(test_path + '/netmap2config')
sys.path.append(test_path + '/netmap2virl')
sys.path.append(test_path + '/topology')
sys.path.append(test_path + '/create_job')
sys.path.append(test_path + '/utils')

import utils
import nmap2virl
import nmap2conf
import license_config
import standard_topologies_defn
import make_tcl_job
import start_dev
import housekeeping
import config_terminal

global const, srvr
report_mail_standard="""

+------------------------------------------------------------------------------+
                                  %s
+------------------------------------------------------------------------------+

Overall Stats:
      %s
      %s
      %s
      %s
      %s
      %s
      %s
%s

Detailed Report: %s 
"""
const="""
testbed:
 name: automation
 alias: automation
 tacacs:
  login_prompt: "login:"
  password_prompt: "password:"
  username: lab
 passwords:
  tacacs: lab
  enable:  lab
  line: lab
 custom:
  owner: iwan-dt

devices:"""
#update username and passwords in the srvr variable
srvr="""
 %s:
  type: 'linux'
  alias: %s
  tacacs:
   username: %s 
  passwords:
   linux: %s
  connections:
   linux:
    protocol: ssh
    ip: '%s'"""

class common_setup():
  
  def parse_and_validate_arguments():
      global testbed
      #global topology_filename
      global csr_image
      global skip_virtual
      global debug
      global log
      global dr, tm

      tm=str('{:%Y-%m-%d_%H:%M:%S}'.format(datetime.datetime.now()))
      dr="logs/"+str(getpass.getuser())+"_"+tm
      os.mkdir(dr)


      
class virtual_harness():
  '''
  This is incremental buildup of test harness
  '''
  proc_name = "tst"
  def create_server_connect_yaml():
    global ds
    ds=dr+"/"+"my.yaml"
    file_handler=open(ds,'w+')
    file_handler.write(const+ srvr %(server_ip,server_ip,user_name, passwrd, server_ip))  
    file_handler.close()

  def create_custom_image(topo):
    global new_name, name_for_server, imageDict
    imageDir = "/home/cisco/image"
    #new_name=re.findall(r'.*/([A-Za-z0-9_.-]+)\.ova', csr_image)[0]
    tb_fl=dr+"/"+topo
    os.mkdir(tb_fl)

    rply=OrderedDict()
    rp=r'uc_send "%s\r"'
    pr=r'\[sudo\] password for %s:'
    rply[pr %user_name]=rp %passwrd
    rply[r'This is your AD password:'] = rp %passwrd
    rply[r'This is your UNIX password:']= rp %passwrd

    testbed=loader.load(ds)
    testbed.devices[server_ip].connect()
    print("Executing command 'cd %s'" %imageDir)
    testbed.devices[server_ip].execute("cd %s" %imageDir)

    #create a set of images
    imageList = []
    imageList.append(transitHubImage)
    imageList.append(branch1Image)
    imageList.append(branch2Image)
    imageList.append(hubImage)
    imageSet = set(imageList)

    print(imageSet)
    imageDict = {}
    image_name_list = []
    for image in imageSet:

      new_name=re.findall(r'.*/([A-Za-z0-9_.-]+)\.ova', image)[0]
      name_for_server=new_name+"_10nic.ova"
      targetDST = imageDir + "/" + name_for_server
      if new_name not in image_name_list:
          image_name_list.append(new_name)
          new_name=targetDST
          k=['cot', '-f','edit-hardware', 'aa', '-o', 'bb', '-c', '2', '-m', '4GB', '-n', '10', '--nic-types' ,'virtio']
          for i in range (0, len(k)):
              if k[i]=="aa":
                  k[i]=image
              if k[i]=="bb":
                 k[i]=new_name

          cot_cmd = ''
          for cmd in k:
              cot_cmd = cot_cmd + cmd + ' '

          print("Executing command '%s'" % cot_cmd)
          op = testbed.devices[server_ip].execute(cot_cmd)    
          # print(op)
          if str(op)!="":
              print(banner("image %s with 10 NICS built" %image))
          else:
              print(banner("Error in building a 10 NIC image from source image. Exiting proc!!!!"))
      if image == hubImage:
        imageDict['hub'] = targetDST
      if image == transitHubImage:
        imageDict['transit'] = targetDST
      if image == branch1Image:
        imageDict['branch1'] = targetDST
      if image == branch2Image:
        imageDict['branch2'] = targetDST
  #this generates VIRL file with input as NETMAP file
  #Converts the interface names according to CSR convention
  #@aetest.skip()
  def create_virl(topo, pi25):
    global img_path, top_nmap, tb_fl
    tb_fl=dr+"/"+topo
    cfg_files=destn
    top=topo
    file=os.listdir(standard_topologies_defn.topology[top])
    for fi in file:
      if ".cfg" or ".virl" in fi:
        dstn=standard_topologies_defn.topology[top]+fi
        shutil.copy(dstn, tb_fl)
    shutil.copy("netmap2virl/laas_increase_q_length.py", tb_fl)
    img_path=destn+"/"+name_for_server
    top_nmap=standard_topologies_defn.topology[top]+"NETMAP"
    nmap2virl.virl_gen(top_nmap , cfg_files, tftp_port, imageDict, tb_fl, pi25)

  #By now we have:VIRL and config files for our topology
  #Copy over the config files via sftp to the server on which 
  #CSR is to be launched
  #Launches the CSR topology
  #changes the queue length
  #@aetest.skip()
  def tb_kickoff(testbed_name):
    import shutil
    files=os.listdir(tb_fl)
    #tftp_dir = "/auto/tftp-sjc-users2/rchaowdh/athena/logs/"+os.path.basename(destn)
    tftp_dir = destn
    #qiangwa comment
    if not os.path.exists(tftp_dir):
        os.makedirs(tftp_dir)
    print(files, tftp_dir)

#   qiangwa modi
    for file in files:
      if ".cfg" or ".virl" in fi:
            print(tb_fl, file, tftp_dir)
            shutil.copy(tb_fl+"/"+file, tftp_dir)
    
    #with pysftp.Connection(server_ip, username=user_name, password=passwrd) as sftp:
    #  if not sftp.exists(destn):
    #      sftp.mkdir(destn, mode=755)
    #  with sftp.cd(destn):
    #    for file in files:
    #      if ".cfg" in file:
    #        src=tb_fl+"/"+file
    #        sftp.put(src)
    #      if ".virl" in file:
    #        src=tb_fl+"/"+file
    #        sftp.put(src)
    #      if ".ova" in file:
    #        src=tb_fl+"/"+file
    #        sftp.put(src)
    #        os.remove(src)
    #      if ".py" in file:
    #        src=tb_fl+"/"+file
    #        sftp.put(src)
    #'''for image in imageDict:
    #  try:
    #    os.remove(imageDict[image])
    #  except:
    #    print("CON")'''
    rply=OrderedDict()
    rp=r'uc_send "%s\r"'
    pr=r'\[sudo\] password for %s:'
    rply[pr %user_name]=rp %passwrd
    rply[r'This is your AD password:'] = rp %passwrd
    rply[r'This is your UNIX password:']= rp %passwrd
    testbed=loader.load(ds)
    testbed.devices[server_ip].connect()
    print("Executing command 'cd %s'" %destn)
    testbed.devices[server_ip].execute("cd %s" %destn)
    print("Executing command 'vmcloud netcreate -v CSR1Kv.virl -t %s'" %testbed_name)
    op=testbed.devices[server_ip].execute("vmcloud netcreate -v CSR1Kv.virl -t %s" %testbed_name, timeout=600)
    #testbed.devices[server_ip].execute("cd ..")
    print(op)
    #qiangwa comment
    #print("Executing command 'python laas_increase_q_length.py'")
    #testbed.devices[server_ip].execute("python laas_increase_q_length.py", timeout=1800, reply=rply)
    #license_config.check_intf_stat(server_ip, testbed_name, "GigabitEthernet1")
    #this proc needs to be called only if xTRs do not have smart license configured
  #Generates the yaml file after the CSR instances are launched
  def create_yaml(testbed_name, topology_name, subject):
    global dd, autoeasy_config
    dd=dr+"/"+testbed_name
    autoeasy_config = nmap2conf.yml_gen(top_nmap, server_ip, testbed_name, user_name, passwrd, dd, topology_name, subject)
  
  def cleanup_dstn():
      print("Clean up")
      with pysftp.Connection(server_ip, username=user_name, password=passwrd) as sftp:
          print("Clean up: connected")
          if sftp.exists(destn):
              print("Clean up: removed")
              sftp.execute("rm -rf %s\n"%destn)

  def cleanup_tftpdir():
      import shutil
      tftp_dir = "/auto/tftp-sjc-users2/rchaowdh/athena/logs/"+os.path.basename(destn)
      if os.path.exists(tftp_dir):
          shutil.rmtree(tftp_dir)
      if os.path.exists(tftp_dir):
          print("ERROR: TFTP directory for %s not removed"%(os.path.basename(destn)))
      else:
          print("TFTP directory for %s removed successfully"%(os.path.basename(destn)))

  def upload_logs(target_dir):
      print("Extracting TRADe link from the report")
      #report_dir = os.path.join(dd, "*.report")
      report_dir = "*.report"
      try:
          print("Current working directory is %s"%(os.getcwd()))
          trade_link = subprocess.check_output('ls -lrt %s'%(report_dir), shell=True)
          trade_link = subprocess.check_output('grep -m 1 -oP "Web Link:\\K.*"  %s'%(report_dir), shell=True)
          trade_link = trade_link.decode("utf-8").strip()
          target_dir = "/srv/icsp/iwan2x/%s"%(target_dir)
          print("Uploading results to fileserver")
          with pysftp.Connection("icsp-fileserver", username="icsp", password="icsp") as sftp:
              if sftp.exists(target_dir):
                  sftp.execute("mv %s/latest.html %s/previous.html"%(target_dir, target_dir))
                  sftp.execute("echo '<meta http-equiv=\"refresh\" content=\"0; url=%s\" />' > %s/latest.html"%(trade_link, target_dir))
                  print("Upload successful")
              else:
                  print("[ERROR] Remote directory does not exist in fileserver")
      except Exception as e:
          print("Unexpected error: ", sys.exc_info()[0], "\n", e) 

  def generate_run_job(scr, testbed_name, job_type, topology_name, unique_id):
    global rprt, dd
    dd=dr+"/"+testbed_name
    mail_recipient = topology_name.split("_")[1]+"@cisco.com"
    script = re.findall(r'.*/(\w+).py', scr)[0]
    #job_name=tm+"_"+"job_"+script+"_"+job_type+".job"
    #jb=tm+"_"+"job_"+script
    job_name = topology_name+".job"
    jb = topology_name
    yaml_path=test_path+"/"+dr+"/"+testbed_name+"/"+testbed_name+".yaml"
    drp=test_path+"/"+dr+"/"+testbed_name
    print(banner(drp))
    os.chdir(drp)
    make_tcl_job.job_make(job_name, scr, yaml_path, 'csr_image', job_type)
    job_location = test_path + "/" + autoeasy_config
    print(banner("Sleeping for 15 minutes for testbed to come up...."))
    time.sleep(300)
    #qiangwa comment
    #nmap2conf.bootstrap_config(topology_name)
    #time.sleep(120)
   # '''ylm=test_path+"/"+dd+"/"+testbed_name+".yaml"
   # print(banner(ylm))
   # start_dev.devices_bringup(ylm)'''
    #config_terminal.set_config_terminal(top_nmap, server_ip, testbed_name, user_name, passwrd, dd, topology_name)
    #print("autoeasy -ni %s -cf %s -mailto %s -mailfrom 'enkins@cisco.com'" %(job_name, job_location, mail_recipient))
    os.environ.clear()
    os.environ["TESTBED"] = "cent-mdc-csr"
    os.environ["AUTOTEST"] = "/opt/ats5.3.0"
    os.environ["ATS_EASY"] = "/opt/ats5.3.0/ats_easy"
    os.environ["PATH"] = "/opt/ats5.3.0/bin:/opt/ats5.3.0/etc:/opt/ats5.3.0/ats_easy/bin:/opt/ats5.3.0/ats_easy/etc:/usr/lib64/qt-3.3/bin:/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/home/qiangwa/bin"
    os.environ["LD_LIBRARY_PATH"] = "/opt/ats5.3.0/lib:/opt/ats5.3.0/ats_lib"
    os.environ["SHELL"] = "/bin/bash"
    os.environ["expect_library"] = "/opt/ats5.3.0/regression/lib"
    os.environ["EXPECT_LIBRARY"] = "/opt/ats5.3.0/regression/lib"
    os.environ["IXIA_HOME"] = "/opt/ats5.3.0/lib"
    os.environ["TAS_PATH"] = "/opt/ats5.3.0/lib/tas"
    os.environ["TCLLIBPATH"] = "/opt/ats5.3.0/lib"
    # os.environ['TESTBED_MAP_FILE'] = "/storage/users/dich/tcl_script/cent/cent_feature/etc/pi25-csr.MAP"
    os.environ['TESTBED_MAP_FILE'] = "/storage/users/dich/tcl_script/0326_PI_cent/cent_feature/etc/pi25-csr.MAP"
    #qiangwa modi 
    #os.system("autoeasy -user %s -mailto %s -ni %s -cf %s -t %s" %(mail_recipient, mail_recipient, job_name, job_location, job_type))
    os.system("autoeasy -mailto %s %s -cf %s" %(mail_recipient,job_name, job_location))

    
    '''fl=os.listdir()
    zp_fldr=str('{:%y-%m}'.format(datetime.datetime.now()))
    for it in fl:
      if zp_fldr==it:
        os.chdir(zp_fldr)
        fil=os.listdir()
        for itm in fil:
          if ".zip" in itm:
            if jb in itm:
              os.system("unzip %s" %itm)
              fl_unpck=os.listdir()
              for ti in fl_unpck:
                if ".report" in ti:
                  if jb in ti:
                    report=open(ti)
                    report=report.read()
                    web_lnk=re.findall(r'^\s*(.+resultsviewer.+\.zip)', report, re.MULTILINE)[0]
                    passed=re.findall(r'^\s*(Passed\s*: \d+)', report, re.MULTILINE)[0]
                    passx=re.findall(r'^\s*(Passx\s*: \d+)', report, re.MULTILINE)[0]
                    failed=re.findall(r'^\s*(Failed\s*: \d+)', report, re.MULTILINE)[0]
                    aborted=re.findall(r'^\s*(Aborted\s*: \d+)', report, re.MULTILINE)[0]
                    blocked=re.findall(r'^\s*(Blocked\s*: \d+)', report, re.MULTILINE)[0]
                    skipped=re.findall(r'^\s*(Skipped\s*: \d+)', report, re.MULTILINE)[0]
                    errored=re.findall(r'^\s*(Errored\s*: \d+)', report, re.MULTILINE)[0]
                    sucess=re.findall(r'^\s*(Success Rate\s*: [0-9.]+ %)', report, re.MULTILINE)[0]
                    rt=re.findall(r'^\s*Success Rate\s*: ([0-9.]+) %', report, re.MULTILINE)[0]
                    mail_rprt=report_mail_standard %(script, passed, passx, failed, aborted, blocked, skipped, errored, sucess, web_lnk)
                    return(mail_rprt)
                cm="echo '%s' | mailx -s '[Harness Job] %s completed at location %s' -c 'jayshar@cisco.com' %s@cisco.com"%(mail_rprt, job_name, drp, getpass.getuser())
        os.system(cm)
        os.chdir(test_path)
        testbed=loader.load(ds)
        testbed.devices[server_ip].execute("cd %s" %destn)
        testbed.devices[server_ip].execute("rm *")'''
class physical_harness():
  '''
  This is physical test harness
  ''' 
  
  def bringup_testbed(testbed):
    global pyml, fll, tid
    tb_fl=dr+"/"+testbed
    os.mkdir(tb_fl)
    os.chdir(tb_fl)
    phy_yml=tb_fl+"/"+testbed+".yaml"
    pyml=test_path+"/"+phy_yml
    fll=test_path+"/"+tb_fl
    lgyml=standard_topologies_defn.topology[testbed]+testbed+"_logical.yaml"
    print(banner(fll))
    print(banner(pyml))
    os.system("python /nobackup/jayshar/py/regression/pyats_labmon/labmon_plugin.py --logical-yaml=%s --labmon-host=cent-labmon01 --physical-yaml=%s"%(lgyml, pyml))
    tid=housekeeping.create_cfg_files(pyml, fll, standard_topologies_defn.topology[testbed])
  def gen_run_job(scr):
    script=re.findall(r'.*/(\w+).py', scr)[0]
    job_name=tm+"_"+"job_"+script+".py"
    jb=tm+"_"+"job_"+script
    make_job.job_make(job_name, scr, pyml, "dummy", cfg_location=fll)
    os.system("easypy -archive_dir %s %s " %(fll, job_name))
    fl=os.listdir()
    print(banner("fl=%s" %fl))
    zp_fldr=str('{:%y-%m}'.format(datetime.datetime.now()))
    for it in fl:
      if zp_fldr==it:
        os.chdir(zp_fldr)
        fil=os.listdir()
        print(banner("fil=%s" %fil))
        for itm in fil:
          if ".zip" in itm:
            if jb in itm:
              os.system("unzip %s" %itm)
              fl_unpck=os.listdir()
              for ti in fl_unpck:
                if ".report" in ti:
                  if jb in ti:
                    report=open(ti)
                    report=report.read()
                    web_lnk=re.findall(r'^\s*(.+resultsviewer.+\.zip)', report, re.MULTILINE)[0]
                    passed=re.findall(r'^\s*(Passed\s*: \d+)', report, re.MULTILINE)[0]
                    passx=re.findall(r'^\s*(Passx\s*: \d+)', report, re.MULTILINE)[0]
                    failed=re.findall(r'^\s*(Failed\s*: \d+)', report, re.MULTILINE)[0]
                    aborted=re.findall(r'^\s*(Aborted\s*: \d+)', report, re.MULTILINE)[0]
                    blocked=re.findall(r'^\s*(Blocked\s*: \d+)', report, re.MULTILINE)[0]
                    skipped=re.findall(r'^\s*(Skipped\s*: \d+)', report, re.MULTILINE)[0]
                    errored=re.findall(r'^\s*(Errored\s*: \d+)', report, re.MULTILINE)[0]
                    sucess=re.findall(r'^\s*(Success Rate\s*: [0-9.]+ %)', report, re.MULTILINE)[0]
                    rt=re.findall(r'^\s*Success Rate\s*: ([0-9.]+) %', report, re.MULTILINE)[0]
                    mail_rprt=report_mail_standard %(script, passed, passx, failed, aborted, blocked, skipped, errored, sucess, web_lnk)
                    return(mail_rprt)

global ip_std

ip_std="""
CSR Image: %s
Server_HostName: %s
Server_Username: %s
Server_Password: %s 
Management_Port: %s
Config_File: %s
"""
if __name__ =="__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("-isPhysical", "--isPhysical", help="[required] Set variable to True for physical testbed, else set it to False", required=True)
  parser.add_argument("-i", "--image", help="[required for virtual testbed] Full path to CSR image. Image should be accessible on this server", required=False)
  parser.add_argument("-c", "--input_configuration", help="[optional] Input configurtion to harness.[default] /ws/jayshar-sjc/test_harness/my_input.yaml", required=False, default="my_input.yaml")
  parser.add_argument("-s", "--server", help="[required for virtual testbed] Server IP address/hostname", required=False)
  parser.add_argument("-u", "--username", help="[required for virtual testbed] Username to connect to the server", required=False)
  parser.add_argument("-p", "--password", help="[required for virtual testbed] Password for username provided to connect with server", required=False)
  parser.add_argument("-m", "--management_port", help="[required for virtual testbed] Management port on the server provided.", required=False)
  parser.add_argument("-d", "--dstn", help="[required for virtual testbed] Full path to location for storing config/ova/virl files in server.", required=False)
  parser.add_argument("-t", "--topology_name", help="[required for virtual testbed] Name to create the topology under", required=False)
  parser.add_argument("-j", "--job_type", help="[required] Type of the job to run", required=True)
  parser.add_argument("-ld", "--logs_dir", help="Logs directory in the fileserver", required=False)
  parser.add_argument("-pi", "--pi25", help="Set to True for pi25 testing, else to False", required=False)
  parser.add_argument("-ui", "--unique_id", help="Unique id for the test", required=False)
  parser.add_argument("-hub_image", "--hub_image", help="[required for virtual testbed] Full path to CSR image for hub routers. Image should be accessible on this server", required=False)
  parser.add_argument("-transit_hub_image", "--transit_hub_image", help="[required for virtual testbed] Full path to CSR image for transit hub routers. Image should be accessible on this server", required=False)
  parser.add_argument("-branch1_image", "--branch1_image", help="[required for virtual testbed] Full path to CSR image for transit Branch1 routers. Image should be accessible on this server", required=False)
  parser.add_argument("-branch2_image", "--branch2_image", help="[required for virtual testbed] Full path to CSR image for transit Branch2 routers. Image should be accessible on this server", required=False)
  parser.add_argument("-deleteTopology", "--deleteTopology",
                            help="[required] Set it to True is the testbed be deleted after running the scripts, else False",
                            required=False, default=True)
  global hubImage, transitHubImage, branch1Image, branch2Image, server_ip, user_name, passwrd, tftp_port, destn, ip
  args = parser.parse_args()
  isPhysical=args.isPhysical
  if isPhysical=="False":
    #csr_image=args.image
    hubImage = args.hub_image
    transitHubImage =args.transit_hub_image
    branch1Image = args.branch1_image
    branch2Image = args.branch2_image
    server_ip=args.server
    user_name=args.username
    passwrd=args.password
    tftp_port=args.management_port
    destn=args.dstn
    ip= args.input_configuration
    topology_name = args.topology_name
    job_type = args.job_type
    logs_dir = args.logs_dir
    pi25 = args.pi25
    unique_id = args.unique_id
    deleteTopology = args.deleteTopology
    fl=open(ip)
    fnl=yaml.safe_load(fl)
    common_setup.parse_and_validate_arguments()
    subject = "%s | H: %s | TH: %s | B1: %s | B2: %s"%(job_type, utils.get_short_image_name(hubImage), utils.get_short_image_name(transitHubImage), utils.get_short_image_name(branch1Image), utils.get_short_image_name(branch2Image))
    for testbed in fnl['test']:
      virtual_harness.create_server_connect_yaml()
      virtual_harness.create_custom_image(testbed)
      virtual_harness.create_virl(testbed, pi25)
      virtual_harness.tb_kickoff(topology_name)
      virtual_harness.create_yaml(testbed, topology_name, subject)
      for script in fnl['test'][testbed]['scripts']:
        rp=virtual_harness.generate_run_job(fnl['test'][testbed]['scripts'][script], testbed, job_type, topology_name, unique_id)
        print(rp)
        es=test_path+"/"+ds
        housekeeping.cleanup(server_ip, es, destn, topology_name, deleteTopology=deleteTopology)
      if logs_dir:
          print(logs_dir)
          virtual_harness.upload_logs(logs_dir)
      #modified by dich
      # if deleteTopology.lower() == "true":
      #     virtual_harness.cleanup_dstn()
      # virtual_harness.cleanup_tftpdir()

    #cm="echo '%s' | mailx -s '[IWAN3_Harness_Job] completed at location %s' -c 'jayshar@cisco.com' %s@cisco.com"%(rp, drp, getpass.getuser())
    #os.system(cm)
      '''tb=loader.load(ds)
      tb.devices[server_ip].connect()
      tb.devices[server_ip].execute("cd %s" %destn, timeout=60)
      tb.devices[server_ip].execute("rm *")
      tb.devices[server_ip].execute("vmcloud netdelete -t %s" %testbed, timeout=500)'''
  elif isPhysical=="True":
    ip= args.input_configuration
    fl=open(ip)
    fnl=yaml.safe_load(fl)
    common_setup.parse_and_validate_arguments()
    for testbed in fnl['test']:
      physical_harness.bringup_testbed(testbed)
      for script in fnl['test'][testbed]['scripts']:
        op=physical_harness.gen_run_job(fnl['test'][testbed]['scripts'][script])
        print((op))
      os.system("python /nobackup/jayshar/py/regression/pyats_labmon/labmon_plugin.py --delete-topo --topo-id=%s --labmon-host=cent-labmon01" %tid)
        




