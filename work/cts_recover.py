#!/usr/bin/env python
#===============================================================================                                                                                       
#                                                                                                                                                                      
#         FILE:  cts_recover.py                                                                                                                                       
#                                                                                                                                                                      
#         DATE:  20XX-XX-XX unknown History unknown, see CC.                                                                                                           
#                2015-01-28 Daniel zeng                                                                                                                               #                2015-12-08 Daniel Zeng Update PGW configure and add sync files  
#
#=============================================================================                                                                                         

import time, sys, re, os
import pexpect
import commands
import subprocess
import logging
import getpass
import urllib2
import json
import tempfile
import datetime

lasttimestamp = int(time.time())

##there is not eqdb for epdg so far, have hardcode one                                                                                                                 
epgcats_path = "/lab/wmg_test_result/tools/wmgcats/20150525/epgcats/"
eqdb_path = "/lab/epg_st_utils/testtools/eqdb"
sync_path = "/lab/wmg_test_result"
ssr_cfg = "/flash/home/erv/ft-ssr-ttcn-platform.conf"

ssh_cmd = "ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no "

debug = True
#debug  = False                                                                                                                                                        

__version__ = "0.6"
__descr__ = """Setup the ssrsim, rebase the ttcn code, compile, copy ttcn build,                                                                                       
             fetch the latest design build and run FT CI from branch."""
pgm = os.path.basename(sys.argv[0])                     # pylint: disable=C0103                                                                                        
_log = logging.getLogger(pgm)                           # pylint: disable=C0103

def get_build_name(build_path):
    build_name = re.findall(".*ewg_cxp9023459_1_(.*)/.*", build_path)
    return build_name[0]

def scp_to(host, src, dst,user, password, timeout=30, bg_run=False):
    if not bg_run:
       sys.stdout.write("\n")
       sys.stdout.flush()
    launchcmd = 'scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o LogLevel=quiet %s %s@%s:%s' % (src,user,host,dst)
    child = pexpect.spawn(launchcmd,timeout=timeout)
    child.logfile_read = sys.stdout
    result=child.expect([pexpect.EOF,"password:",">"])
    if result== 1:
       child.sendline(password)
       result1 = child.expect([pexpect.EOF,">"])
   
    child.close()

def print_log(str):
    ctime= datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sys.stdout.write("\n### "+ctime+" "+str)
    sys.stdout.flush()

def cmdline(command):
    result = os.system(command)
    return result
    
def init():
    """ Setup program input options and arguments. """
    from argparse import ArgumentParser, RawDescriptionHelpFormatter
    global args, _log

    parser = ArgumentParser(prog=pgm, description=__descr__,
                            formatter_class=RawDescriptionHelpFormatter)

    parser.add_argument("-b", "--build", metavar= 'package', action="store", dest="wmg_build", default = None,
                            help="Absolute path to wmg service build")

    parser.add_argument("-n", "--node", metavar= 'n', action='store', dest="node", required=True,
                            default=None, help="Destination ssrsim chassis. Default is epg140-1" )

    parser.add_argument("-u", "--upgrade", action='store_true', dest="upgrade",default= None,
                        help="Add this if to upgrade the service,it will erase the previoues service firstly")
    
    parser.add_argument("-p", "--pgw", action='store', dest="pgw_build",default= None,
                        help="Add this if to install PGW simulator")

    parser.add_argument("-w", "--web_recover", action='store_true', dest="recover_web",default= None,
                        help="Add this if to recover web")

    parser.add_argument("-a", "--app_recover", action='store_true', dest="recover_app",default= None,
                        help="Add this if to recover app")

    parser.add_argument("-s", "--scripts_recover", action='store_true', dest="recover_scripts",default= None,
                        help="Add this if to recover scripts")

    parser.add_argument("-c", "--ssrsim_cfg", action='store', dest="service_cfg",default= "./cwagcfg.txt",
                        help="Path+filename of ssrsim configuration file, add if is not \"./cwagcfg.txt\"")

    parser.add_argument("-v", "--project_version", metavar= 'v', action='store', dest="project", required=True,
                            default=None, help="version of the project ,15B or 16B" )    

    parser.add_argument("-f", "--add_config", action='store_true', dest="add_config", default=None,
                        help="Add this if to generate add_cofig file" )    

    args = parser.parse_args()
    #print(args)               
def check_host(node_number):
    system_name = os.getenv('HOSTNAME')
    node_name = system_name[7:12]
    if node_number.find(node_name) == -1:
        print_log("Can not run this script at "+system_name+" with "+node_number+ "\n")
        sys.exit(0)

def check_tool_init():
     if cmdline("ping -c 1 11.0.1.181 >/dev/null 2>&1"):
        return False
     if cmdline("ping -c 1 11.0.1.254 >/dev/null 2>&1"):
        return False
     else:
        return True

def get_node_id(node_number):
    return node_number[7:]

def get_node_id(node_number):
    return node_number[7:]

#This function is to combind the pexpect cmd and expect response	
def auto_send(child, cmd, response):
	child.sendline(cmd)
	child.expect(response)

def vlan_setup(node_number):
    print_log("EQDB:Started to configure vlans and routes")
    eqdb_cmd = "/lab/epg_st_utils/bin/eqdb_tool -create chn %s -outline 0 -ttcn 1 -mns 0 -force" % node_number
    #some bug for eqdb_tool,no fix ,some pingbi follow command.
    if debug:
        print eqdb_cmd
    #response = subprocess.call(eqdb_cmd,
    #        shell=True,
    #        stdout=open('/dev/null', 'w'),
    #        stderr=subprocess.STDOUT)
    
    #if response == 1:
    #   print "\nConfig vlan error, quit now"
    #   sys.exit(0)

    vlan_cmd = "/lab/epdg/tools/wmgcats/20150525/cwagvlan_setup.sh " + node_number + " /lab/epdg/tools/wmgcats/20150525/testtoolsetup_cwag.sh"
    if debug:
        print vlan_cmd
    response = subprocess.call(vlan_cmd,
            shell=True,
            stdout=open('/dev/null', 'w'),
            stderr=subprocess.STDOUT)
       # update the bar                                                                                                                                                
    if response == 1:
       print "\nConfig vlan error, quit now"
       sys.exit(0)

def kill_pgw(child):
    child.sendline('ps -ef|grep lma')
    child.expect('#')
    r = re.compile(r'root\s+(\d*)\s+.*dtach.*lma')
    for m in r.finditer(child.before):
        pid = m.group(1)
        
    while not pid:
            time.sleep(2)
            sys.stdout.flush()
            child.sendline('ps -ef|grep lma')
            child.expect('#')
            r = re.compile(r'root\s+(\d*)\s+.*dtach.*lma')
            for m in r.finditer(child.before):
                pid = m.group(1)

    print 'Here is lma process : %s' % pid
    child.sendline('kill -9 ' + pid)
    child.expect('#')
    
def restart_pgw(child):
    sys.stdout.flush()
    child.sendline("/etc/init.d/ha restart")
    result = child.expect(["Start ha Success","Start ha Failed"],timeout=320)
    while result:
        print_log("start ha failed, try to kill pgw \n")
        pid = ''
        while not pid:
            time.sleep(2)
            sys.stdout.flush()
            child.sendline('ps -ef|grep lma')
            child.expect('#')
            r = re.compile(r'root\s+(\d*)\s+.*dtach.*lma')
            for m in r.finditer(child.before):
                pid = m.group(1)
                print 'Here is lma process : %s' % pid

        child.sendline('kill -9 ' + pid)
        time.sleep(5.0)
        child.sendline('ps -ef|grep lma')
        child.expect('#')
        while 'dtach-ma' not in child.before:
            child.sendline('ps -ef|grep lma')
            sys.stdout.flush()
            child.expect('#')
            
        child.sendline("/etc/init.d/ha restart")
        result = child.expect(["Start ha Success","Start ha Failed"])
    print_log("Restart PGW Sim success !!!\n")

def install_pgw_sim(node_number,pgw_build,cfg_file,restart_only=False):   
    epgtool = "epgtool" + node_number.split("epg")[1] + "1"
    if not restart_only:
        print_log("Start to install PGW Simulator")
        pgw_cmd = "/lab/epg_st_logs/ervmape/st/tools/cwag/cwagvlan_setup.sh " + node_number + " install_utsnt /lab/epdg/epdg_tools/pgw_load/utsnt-ha_5.2.0-5-9218_i386.deb"
        print "epgtool is : " + epgtool

        if debug:
            print pgw_cmd

            response = subprocess.call(pgw_cmd,
                                       shell=True,
                                       stdout=open('/dev/null', 'w'),
                                       stderr=subprocess.STDOUT)
        if response == 1:
            print "\nConfig PGW error, quit now"
            sys.exit(0)
            
        
        child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no root@%s" % epgtool, timeout = 300*300)
    
        if debug:
            child.logfile_read=sys.stdout

        result = child.expect(["#","password:"])
        if result ==1:
            child.sendline("lmc_xdg")
            child.expect("#")

        ### Configure PGW Simulator ###
        auto_send(child, "rm -rf /opt/utsnt/run/ma/*", "#")
        auto_send(child, "rm -rf /tmp/dtach-ha", "#")
        auto_send(child, "cp %s/wmg_cts_recover/installation_files/neconfig.dat /opt/utsnt/run/ma/" %sync_path, "#")
        restart_pgw(child)
        child.sendline("~/shell.sh")
        result2 = child.expect(["Win%", "#"])
        while result2:
            time.sleep(2.0)
            child.sendline("~/shell.sh")
            result2 = child.expect(["WinG%", "#"])
            
        auto_send(child, "exit", "%")            
        auto_send(child, "sv", "System Uptime")
        child.close()

        ### Update PGW Simulator to the specific one ###
        time.sleep(5.0)
        print_log("Start to update PGW Simulator to the specific one !\n\n")
        pgw_cmd = "/lab/epg_st_logs/ervmape/st/tools/cwag/cwagvlan_setup.sh " + node_number + " install_utsnt /lab/epdg/epdg_tools/pgw_load/" + pgw_build
        if debug:
            print pgw_cmd
            response = subprocess.call(pgw_cmd,
                                       shell=True,
                                       stdout=open('/dev/null', 'w'),
                                       stderr=subprocess.STDOUT)
            if response == 1:
                print "\nConfig PGW error, quit now"
                sys.exit(0)
                
        ### check PGW version after update ###
        print_log("check PGW version after update\n")
        child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no root@%s" % epgtool, timeout = 300*300)
    
        if debug:
            child.logfile_read=sys.stdout

        result = child.expect(["#","password:"])
        if result ==1:
            child.sendline("lmc_xdg")
            child.expect("#")

        restart_pgw(child)
        child.sendline("~/shell.sh")
        result2 = child.expect(["Win%", "#"])
        while result2:
            time.sleep(2.0)
            child.sendline("~/shell.sh")
            result2 = child.expect(["WinG%", "#"])
            
        auto_send(child, "exit", "%")            
        auto_send(child, "sv", "System Uptime")
        child.close()

    else:
        child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no root@%s" % epgtool, timeout = 300*300)
        print_log("Only to restart PGW Simulator")

        restart_pgw(child)
        child.close()
        
    print "\nPGW Installation done!"
       


def make_basic_ssr_conf(node_number):
    print_log("EQDB:Generate basic ssr configuration and scp to node")
    subprocess.call("setenv EQDBPATH "+eqdb_path,
            shell=True,
            stdout=open('/dev/null', 'w'),
            stderr=subprocess.STDOUT)

    gen_cmd = "/usr/bin/make -BC "+ epgcats_path + " usergen/" + node_number + "/" + node_number + ".epg_platform.basic.conf useEpdg=1"
    gen_path = epgcats_path + "usergen/" + node_number + "/" + node_number + ".epg_platform.basic.conf"
    if debug:
       print gen_cmd
       print gen_path
    response = subprocess.call(gen_cmd,
            shell=True,
            stdout=open('/dev/null', 'w'),
            stderr=subprocess.STDOUT)
    if response == 1:
       print "SSR cfg generate error, quit now"
       sys.exit(0)
    time.sleep(1)
    if cmdline("ls "+gen_path):
       print "can not generate the ssr configuration file, exit now"
       sys.exit(0)

    ### Workaround to fix the cli change issue ###
    file =open(gen_path)
    file_list = list()
    file_list = file.readlines()

    for i in range(len(file_list)):
        if "Epdg" in file_list[i]:
            file_list[i] = file_list[i].replace("Epdg","Wmg")

        if "epdg" in file_list[i]:
            file_list[i] = file_list[i].replace("asp pool epdg service epdg","asp pool epdg service wmg")

    file_out = open(gen_path,"w")
    file_out.writelines(file_list)
    file.close()
    file_out.close()

    ### Workaround End ### 

    scp_to(node_number, gen_path, ssr_cfg,"root", "root", 300, True)
    
def configure_erv(node_number,cfg_name):
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no erv@%s" % node_number, timeout = 300*300)
    if debug:
       child.logfile_read=sys.stdout
    result=child.expect([node_number+"#","password:"])
    if result == 1:
       child.sendline("ggsn")
       child.expect(node_number + "#")
    scp_to(node_number, cfg_name, "/flash/home/erv/"+cfg_name,"root", "root", 300, True)
    child.sendline("configure /flash/home/erv/"+cfg_name)
    child.expect(node_number + "#")
    child.close()

def configure_save_ipos(node_number):
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no erv@%s" % node_number, timeout = 300*300)
    if debug:
       child.logfile_read=sys.stdout
    result=child.expect([node_number+"#","password:"])
    if result == 1:
       child.sendline("ggsn")
       child.expect(node_number + "#")
    child.sendline("save configuration ericsson.cfg -noconfirm")
    child.expect(node_number + ".*#")
    child.close()

def configure_cfg(node_number,cfg_name,reload=True):
    print_log("Start to configure node with ssr configuration ")
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no erv@%s" % node_number, timeout = 300*300)
    if debug:
       child.logfile_read=sys.stdout
    result=child.expect([node_number+"#","password:"])
    if result == 1:
       child.sendline("ggsn")
       child.expect(node_number + "#")
    child.sendline("copy /flash/home/erv/ft-ssr-ttcn-platform.conf /flash/ericsson.cfg -noconfirm")
    child.expect(node_number+"#")
    if reload:
       child.sendline("reload")
       result = child.expect(["configuration\? \(y\/n\)","want to reload\? \(y\/n\)"])
       if result == 0:
           child.sendline("n")
           child.expect("want to reload\? \(y\/n\)")
           child.sendline("y")
           child.expect("Start to reload system")
       if result == 1:
           child.sendline("y")
           child.expect("Start to reload system")

    child.close()

def copy_file(node_number,src,dst):
    print_log("Copy from "+src+" to "+dst)
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no root@%s" % node_number, timeout = 300*300)
    #child.logfile_read=sys.stdout                                                                                                                                          
    result=child.expect([node_number+".*>","password:"])
    if result == 1:
       child.sendline("root")
       child.expect("root>")
    if debug:
       child.logfile_read=sys.stdout

    child.sendline("cp "+src+" "+dst)
    child.expect("root>")
    child.sendline("cat " +dst)
    child.expect("root>")
    child.close()

    ##cmdline("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no root@"+node_number+" cp "+src+" "+dst):                             


def prepare_without_ewgbuild(node_number):
    ###eqdb setup                                                                                                                                                      
    vlan_setup(node_number)
    ###genreate cfg at first                                                                                                                                           
    #make_basic_ssr_conf(node_number)
    #configure_erv(node_number,"erv_key_cwag.cfg")                                                                                                                     
    #config_asp(node_number,basic_ssr_cfg)  
    #configure_save_ipos(node_number)
        
def ping_node(node_number):
    print_log("Ping node "+node_number+" during node restart")
    while True:
       response = subprocess.call("ping -c 1 %s" % node_number,
            shell=True,
            stdout=open('/dev/null', 'w'),
            stderr=subprocess.STDOUT)
       # update the bar                                                                                                                                                
       if response == 1:
          sys.stdout.write(".")
          sys.stdout.flush()
          time.sleep(0.1)
       else:
          break
    time.sleep(10)
    print_log("Try to ssh node "+node_number)
    for loop_count in range(1, 600):
         child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no erv@%s" % node_number, timeout = 10)
         try:
             if debug:
                 child.logfile_read=sys.stdout
                 result = child.expect([pexpect.TIMEOUT,node_number+"#","password:"])
                 if result == 0:
                     sys.stdout.write("*")
                     sys.stdout.flush()
                     time.sleep(0.1)
                 if result == 1:
                     child.close()
                     break
                 if result == 2:
                     child.sendline("ggsn")
                     gresult=child.expect([node_number+"#","Permission denied","password:",pexpect.TIMEOUT],timeout=120)
                     if gresult == 0:
                         child.close()
                         break
                     else:
                         fix_ssh_erv(node_number)
                 child.close()
         except pexpect.EOF:                 
             sys.stdout.write("*")
             sys.stdout.flush()
             time.sleep(0.1)
    print_log("Node "+node_number+ " is up!")
    
def fix_ssh_erv(node_number):
    print_log("SSH Key is wrong, fix it now")
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no root@%s" % node_number, timeout = 300*300)
    result=child.expect([node_number+".*>","password:"])
    if result == 1:
       child.sendline("root")
       child.expect("root>")
    if debug:
       child.logfile_read=sys.stdout

    child.sendline("rm /flash/home/erv/.ssh/authorized_keys")
    child.expect("root>")
    child.sendline("rm /flash/home/erv/.ssh/known_hosts")
    child.expect("root>")
    child.sendline("pkill -f /usr/sbin/sshd")
    child.expect("root>")
    child.sendline("pkill -f /usr/lib/siara/bin/ssh_auth_server")
    child.expect("root>")

    child.close()
    time.sleep(5)
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no erv@%s" % node_number, timeout = 300*300)
    result=child.expect([node_number+"#","password:"],timeout=120)
    if result == 1:
       child.sendline("ggsn")
       child.expect(node_number+"#")

    child.close()
def check_card(node_number):
    print_log("Check if all card is up ")
    ssrsim_type = str()
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no dev@%s" % node_number, timeout = 300*300)
    child.logfile_read = sys.stdout
    result=child.expect(["#","password:"],timeout=120)
    if result == 1:
       child.sendline("dev")
       child.expect(node_number+"#",timeout=120)
    else:
        print result


    #Check the ssrsim is large or small
    child.sendline("show card")
    child.expect(node_number+"#")
    strings = re.findall(r':\s+ssc1\s', child.before)
    if len(strings) == 2:
        card_num = 2
        ssrsim_type = "small"
        print("#####  SSRSIM is %s, card number is: %s  #####\n" % (ssrsim_type, card_num))

    if len(strings) == 4:
        card_num = 4
        ssrsim_type = "large"
        print("#####  SSRSIM is %s, card number is: %s  #####\n" % (ssrsim_type, card_num))

    else:
        print("#####  SSRSIM Type double check ### ")
    
    while True:
       child.sendline("show card")
       child.expect(node_number+"#")
       strings = re.findall(r'ssc1\s+ssc1\s+IS\s+In\sService', child.before)
       if len(strings) >= card_num:
          break
       else:
          sys.stdout.write(".")
          sys.stdout.flush()
          time.sleep(2.5)

    print_log("All card is in service!")

    return ssrsim_type
    child.close()

def install_service(node_number,cwag_build):
    service_name = "/md/cwag_temp_service_package.tar.gz"
    scp_to(node_number, cwag_build, service_name,"root", "root", 300, False)

    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no erv@%s" % node_number, timeout = 300*300)

    if debug:
      child.logfile_read = sys.stdout

    result=child.expect([node_number+"#","password:"])
    if result == 1:
       child.sendline("ggsn")
       child.expect(node_number+"#")
    print_log("Installing cwag service package ")
    while True:
          child.sendline("release download service "+service_name)
          result = child.expect(node_number + ".*#")
          if "Release distribution failed" in child.before:
             sys.stdout.write(".")
             sys.stdout.flush()
             time.sleep(2.5)
          else:
             if "Release distribution completed" in child.before:
                 break
    print_log("Cwag service install successfully!")
#    print_log("Start to reload to finish the asp configure.")
    print_log("Start to configure cfg file to finish the asp configure.")
    auto_send(child, "configure /flash/ericsson.cfg besteffort implicit", "#")

    print("\n")
    """
    child.sendline("reload")
    result = child.expect(["configuration\? \(y\/n\)","want to reload\? \(y\/n\)"])
    if result == 0:
        child.sendline("n")
        child.expect("want to reload\? \(y\/n\)")
        child.sendline("y")
        child.expect("Start to reload system")
    if result == 1:
        child.sendline("y")
        child.expect("Start to reload system")
    """
    child.close()
    

def uninstall_service(node_number,ssrsim_type):
    service_name = "wmg"
    uninstall = 0

    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no dev@%s" % node_number, timeout = 300*300)
    if debug:
        child.logfile_read = sys.stdout
    result=child.expect([node_number+"#","password:"])

    if result == 1:
        child.sendline("dev")
        index = child.expect([node_number+"#","password:"])
        if index == 0:
            uninstall = 0
        if index == 1:
            child.sendline()
            child.close()
            time.sleep(1)
            child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no dev@%s" % node_number, timeout = 300*300)
            if debug:
                child.logfile_read = sys.stdout
            result=child.expect("password:")
            child.sendline("dev")
            child.expect(node_number+"#")

    print_log("Uninstalling cwag service package ")
    child.sendline("st o")
    child.expect(">")
    child.sendline("ManagedElement=1")
    child.expect(">")
    child.sendline("configure")
    child.expect(">")
    child.sendline("WmgFunction=1")
    child.expect(">")
    child.sendline("no SystemManagement=1")
    child.expect(">")
    child.sendline("up")
    child.expect(">")
    child.sendline("no WmgFunction=1")
    child.expect(">")
    child.sendline("commit")
    child.expect(">")
    child.sendline("top")
    child.expect(">")
    child.sendline("exit")
    child.expect("#")

    if ssrsim_type == "small":
        cmd = """configure
asp default_asp_attr 5 / 1
shutdown
exit
asp default_asp_attr 15 / 1
shutdown
exit
asp default_asp_attr management / 1
shutdown
exit
asp pool epdg service wmg
no asp 5 / 1
no asp 15 / 1
no asp management / 1
commit
end
"""

    if ssrsim_type == "large":
        cmd = """configure
asp default_asp_attr 5 / 1
shutdown
exit
asp default_asp_attr 15 / 1
shutdown
exit
asp default_asp_attr 16 / 1
shutdown
exit
asp default_asp_attr 17 / 1
shutdown
exit
asp default_asp_attr management / 1
shutdown
exit
asp pool epdg service wmg
no asp 5 / 1
no asp 15 / 1
no asp 16 / 1
no asp 17 / 1
no asp management / 1
commit
end
"""


    cmd_list = cmd.split("\n")

    for line in  cmd_list:
        if not line:
            break
        else:
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(0.1)
            child.sendline(line)
            child.expect("#")
 
    child.sendline("save configuration")
    child.expect("write?")
    child.sendline("y")
    child.expect(node_number+"#")
    child.sendline("configure")
    child.expect("#")
    child.sendline("no asp pool epdg")
    child.expect("#")
    child.sendline("commit")
    child.expect("#")
    child.sendline("exit")
    child.expect("#")

    while True:
        child.sendline("release erase service "+ service_name)
        child.expect("(y/n)")
        child.sendline("y")
        child.expect(node_number+"#")
        child.sendline("show release service native")
        child.expect("#")
        #print "child.before is : " + child.before + "end\n"                                                                                                           
        if service_name not in child.before:
            break
        else:
            #sys.stdout.write(".")                                                                                                                                     
            sys.stdout.flush()
            time.sleep(1.0)

    print_log("Cwag service uninstall successfully!")
    child.close()

def config_epdg(node_number,cfg_file):
    print_log("Config epdg service part ongoing ")
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no dev@%s" % node_number, timeout = 300*300)
    #child.logfile_read=sys.stdout                                                                                                                                          
    result=child.expect([node_number+"#","password:"])
    if result == 1:
       child.sendline("dev")
       child.expect(node_number+"#")
    if debug:
       child.logfile_read=sys.stdout
    print_log("sleep 10s to wait com active\n")
    time.sleep(10.0)
    
    child.sendline("start oam-cli")
    child.expect(">")
    child.sendline("configure")
    child.expect(".*>")
    child.sendline("ManagedElement=1")
    child.expect(".*>")

    cfile = open(cfg_file)
    while True:
      line = cfile.readline()
      if not line:
         break
      else:
         sys.stdout.write(".")
         sys.stdout.flush()
         time.sleep(0.1)
         child.sendline(line)

    child.sendline("commit")
    child.expect(".*>")
    child.sendline("exit")
    child.expect(node_number+"#")
    child.sendline("save configuration ericsson.cfg -noconfirm")
    child.expect(node_number + ".*#")

    child.close()
    scp_to(node_number, cfg_file, "/flash/home/erv/ft-ssr-ttcn-services-mpg.conf","root", "root", 300, True)
    

def check_asp(node_number,asp_num):
    print_log("Check if all asp is up ")
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no dev@%s" % node_number, timeout = 300*300)
    result=child.expect([node_number+"#","password:"])
    if result == 1:
       child.sendline("dev")
       child.expect(node_number+"#")
    if debug:
       child.logfile_read = sys.stdout
    count = 0
    while True:
       if count == 100:
          print "fault in wait asp, maybe the build is not install correctly"
          sys.exit(0)
       child.sendline("show asp")
       child.expect(node_number+"#")
       strings = re.findall(r'IS\s+IS\s+epdg\s+wmg', child.before)
       if len(strings) >= asp_num:
          break
       else:
          sys.stdout.write(".")
          sys.stdout.flush()
          time.sleep(2.5)
    print_log("All ASP is in wmg service!")
    child.close()

def check_wmg(node_number):
    print_log("Check if wmg COM is up ")
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no  dev@%s" % node_number, timeout = 300*300)
    result=child.expect([node_number+"#","password:"])
    if result == 1:
       child.sendline("dev")
       child.expect(node_number+"#")
    if debug:
       child.logfile_read=sys.stdout

    child.sendline("start oam-cli")
    child.expect(">")
    child.sendline("configure")
    child.expect(">")
    child.sendline("ManagedElement=1")
    child.expect(">")
    child.sendline("WmgFunction=1")
    child.expect(">")
    if "ERROR: Command not found." in child.before:
        child.sendline("end")
        child.expect(">")
        child.sendline("exit")
        child.expect(node_number+"#")
        child.sendline("save configuration ericsson.cfg -noconfirm")
        child.expect(node_number + "#")
        child.sendline("reload")
        child.expect("you really want to reload\? \(y\/n\)")
        child.sendline("y")
        time.sleep(30)
        print_log("Wmg function can not work in COM, reload node ")
        child.close()
        return 0
    print_log("Ready to configure with wmg now")
    child.sendline("abort")
    child.expect(">")
    child.sendline("exit")
    child.expect("#")
    child.close()
    return 1

def check_wmg_service(node_number,asp_num):
    print_log("Check if wmg service is up ")
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no dev@%s" % node_number, timeout = 300*300)
    result=child.expect([node_number+"#","password:"])
    if result == 1:
       child.sendline("dev")
       child.expect(node_number+"#")
    if debug:
       child.logfile_read=sys.stdout

    child.sendline("start oam-cli")
    child.expect(">")
    child.sendline("configure")
    child.expect(">")
    child.sendline("ManagedElement=1")
    child.expect(">")
    child.sendline("WmgFunction=1")
    child.expect(">")
    child.sendline("SystemManagement=1")
    child.expect(">")
    for count in range(0,30):
       child.sendline("showSystem")
       child.expect(">")
       strings = re.findall(r'System Uptime', child.before)
       if len(strings) >= asp_num:
           break
       else:
          sys.stdout.write(".")
          sys.stdout.flush()
          time.sleep(1.0)
          
    print_log("wmg service is up now")
    child.close()

def config_mtu(node_number):
    print_log("Config wic configuration for cwag.")
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no root@%s" % node_number, timeout = 300*300)
    result=child.expect([node_number+".*>","password:"])
    if result == 1:
       child.sendline("root")
       child.expect("root>")
    if debug:
       child.logfile_read=sys.stdout

    child.sendline("ssh -o StrictHostKeyChecking=no root@lc-5")
    child.expect("password:")
    child.sendline("root")
    child.expect("root>")
    #child.sendline("ifconfig ifvfab mtu 3072 up")
    #child.expect("root>")
    #child.sendline("ifconfig lc0 mtu 3072 up")

def config_cwag(node_number,cfg_file):
    print_log("Config wic configuration for cwag.")
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no root@%s" % node_number, timeout = 300*300)
    result=child.expect([node_number+".*>","password:"])
    if result == 1:
       child.sendline("root")
       child.expect("root>")
    if debug:
       child.logfile_read=sys.stdout

    child.sendline("ssh -o StrictHostKeyChecking=no root@lc-5")
    child.expect("password:")
    child.sendline("root")
    child.expect("root>")
    child.sendline("/opt/services/wmg/p01/bin/dtach -a /tmp/dtach-wmg")
    child.expect("WinG%")

    cfile = open(cfg_file)
    while True:
      line = cfile.readline()
      if not line:
         break
      else:
         sys.stdout.write(".")
         sys.stdout.flush()
         time.sleep(0.1)
         child.sendline(line)
         
    child.expect("WinG%")
    #child.close()                                                                                                                                                     
def recover_app(node_number, ssrsim_type):
    print_log('Start to recover app!')
    if args.project == '15B':
        sync_repo = 'wmg_cts_recover'
    elif args.project == '16B':
        sync_repo = 'wmg_cts_recover_16B'
    else:
        print_log("not vlaid project num ,please choose a correct one!!!")
        sys.exit(1)

    node = "epgtool" + node_number.split('epg')[1] + "2"
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no root@%s" % node, timeout = 300*300)
    child.logfile_read = sys.stdout
    result = child.expect(["#","password:"])
    if result ==1:
        child.sendline("lmc_xdg")
        child.expect("#")

    cmd_app = """
cp /home/echumen/udp_tester_1000.py /var/www/
cp /home/echumen/Packages.gz /var/www/
cp /home/echumen/vsftpd_3.0.2-1ubuntu2.14.04.1_amd64.deb /var/www/
cp /home/echumen/vsftpd.conf /var/www/
dpkg -i /var/www/vsftpd_3.0.2-1ubuntu2.14.04.1_amd64.deb
mv /etc/vsftpd.conf /etc/vsftpd.conf_bak
cp /var/www/vsftpd.conf /etc/
mkdir /var/ftp
cp /home/echumen/1M /var/ftp
service vsftpd restart
cp /home/echumen/sshpass_1.05-1_amd64.deb /var/www/
dpkg -i /var/www/sshpass_1.05-1_amd64.deb
cp sync_path_str/lrzsz_0.12.21-7_amd64.deb /tmp/
dpkg -i /tmp/lrzsz_0.12.21-7_amd64.deb
cp sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/cts* /opt/cts/CTS/ssr_epdg/regression_cases/.
cp sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/ssr_epdg_regression_config.pm /opt/cts/CTS/ssr_epdg/regression_cases/.
cp sync_path_str/target_repo/CTS/Core/TestCase.pm  /opt/cts/CTS/Core/TestCase.pm
cp sync_path_str/target_repo/CTS/ssr_epdg/common_tool.pm /opt/cts/CTS/ssr_epdg/.
cp -R sync_path_str/target_repo/CTS/ssr_epdg/takeover_cases /opt/cts/CTS/ssr_epdg/.
cp -R sync_path_str/target_repo/CTS/ssr_epdg/twag_cases /opt/cts/CTS/ssr_epdg/.
cp sync_path_str/target_repo/installation_files/auto_ssrsim*.pl /opt/cts/installation_files/.
cp sync_path_str/target_repo/installation_files/LN_Lab.cfg /opt/cts/installation_files/.
cp /home/echumen/cts_crontab.pl /var/.
echo '00 13   * * *   root    /var/cts_crontab.pl' >> /etc/crontab
"""
    cmd_app = cmd_app.replace('sync_path_str', sync_path).replace('target_repo', sync_repo)
    cmd_list_app = cmd_app.split("\n")
    for cmd in cmd_list_app:
        child.sendline(cmd)
        child.expect("#")

    cmd_sed = "sed -i "+"\"s/epg1xx-x/"+"%s/g\"  /opt/cts/installation_files/LN_Lab.cfg" % node_number
    auto_send(child, cmd_sed, "#")
    if ssrsim_type == "large" :
        #Replace the 4 asps switch to yes
        cmd_sed_ssc = "sed -i "+"\"s/fourth-ssc-card = no/"+"fourth-ssc-card = yes/g\"  /opt/cts/installation_files/LN_Lab.cfg"
        auto_send(child, cmd_sed_ssc, "#")

    child.close()


def recover_web(node_number):
    node = "epgtool" + node_number.split('epg')[1] + "2"
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no root@%s" % node, timeout = 300*300)
    child.logfile_read = sys.stdout
    result = child.expect(["#","password:"])
    if result ==1:
        child.sendline("lmc_xdg")
        child.expect("#")

    cmd_web ="""
cd /opt/cts/installation_files/

"""
    cmd_list_web = cmd_web.split("\n")
    for cmd in cmd_list_web:
        child.sendline(cmd)
        child.expect("#")

    child.close()

def recover_script(node_number):
    if args.project == '15B':
        sync_repo = 'wmg_cts_recover'
    elif args.project == '16B':
        sync_repo = 'wmg_cts_recover_16B'
    else:
        print_log("not vlaid project num ,please choose a correct one!!!")
        sys.exit(1)
    
    node_strongswan = "epgtool" + node_number.split('epg')[1] + "0"
    node_others = "epgtool" + node_number.split('epg')[1] + "1"

    ### Configure strongswan ###
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no root@%s" % node_strongswan, timeout = 300*300)
    child.logfile_read = sys.stdout
    result = child.expect(["#","password:"])
    if result ==1:
        child.sendline("lmc_xdg")
        child.expect("#")

    cmd_strongswan = """
cd /usr/local/etc
cp -R sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/strongswan/* ./ 
perl -i -pe 's/88\.0\.44\./117.0.0./ig' strongsw*.* 
perl -i -pe 's/5680:44:/2a01:4001:/ig' strongsw*.*
cd /root
mkdir .wireshark
cp /home/echumen/iptables_1.4.21-1ubuntu1_amd64.deb /tmp
cp -R sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/twag_ue_simulator /opt/.
cp /home/echumen/strongswan-5.1.0.13.tar.gz /tmp
cp /home/echumen/xperf_dpdk_testbed_vlan_1.3.tar.bz2 /mnt
cd /mnt
tar -vxf xperf_dpdk_testbed_vlan_1.3.tar.bz2
cp /home/echumen/system.cfg /mnt/scripts/
cp /home/echumen/grub.cfg /boot/grub/
cp /home/echumen/fstab /etc/
cd /tmp
dpkg -i iptables_1.4.21-1ubuntu1_amd64.deb
tar -vxzf strongswan-5.1.0.13.tar.gz
cd /tmp/strongswan-5.1.0
./build_install.pl
cp sync_path_str/lrzsz_0.12.21-7_amd64.deb /tmp/
dpkg -i /tmp/lrzsz_0.12.21-7_amd64.deb
"""
    cmd_strongswan = cmd_strongswan.replace('sync_path_str', sync_path).replace('target_repo', sync_repo)
    cmd_list_strongswan = cmd_strongswan.split("\n")

    for cmd in cmd_list_strongswan :
        child.sendline(cmd)
        child.expect("#")

    child.close()

    ### Configure twag_simulator###
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no root@%s" % node_strongswan, timeout = 300*300)
    child.logfile_read = sys.stdout
    result = child.expect(["#","password:"])
    if result ==1:
        child.sendline("lmc_xdg")
        child.expect("#")

    cmd_twag_sim = """
cp -rf sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/twag_ue_simulator/* /opt/twag_ue_simulator/
"""
    cmd_twag_sim = cmd_twag_sim.replace('sync_path_str', sync_path).replace('target_repo', sync_repo)
    cmd_list_twag_sim = cmd_twag_sim.split("\n")

    for cmd in cmd_list_twag_sim :
        child.sendline(cmd)
        child.expect("#")

    child.close()


    FM_wrong = "sync_path_str/%s/installation_files/FM_wrong_file/ca.crt_bad" % sync_repo
    service_name = "/home/"
    scp_to(node_number, FM_wrong, service_name,"root", "root", 300, False)
    FM_wrong = "sync_path_str/%s/installation_files/FM_wrong_file/ca.crt_good" % sync_repo
    service_name = "/home/"
    scp_to(node_number, FM_wrong, service_name,"root", "root", 300, False)
    FM_wrong = "sync_path_str/%s/installation_files/FM_wrong_file/wmg_old" % sync_repo
    service_name = "/home/"
    scp_to(node_number, FM_wrong, service_name,"root", "root", 300, False)

    ### Configure dns ###
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no root@%s" % node_others, timeout = 300*300)
    child.logfile_read = sys.stdout
    result = child.expect(["#","password:"])
    if result ==1:
        child.sendline("lmc_xdg")
        child.expect("#")

    cmd_dns = """
cd /var/named 
rm -rf * 
cp sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/dns-server/named/named.conf named.rfc1912.zones 
cp sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/dns-server/named/* . 
chmod -R 777 /var/named 
perl -i -pe 's/10.56.104.44/11.10.1.76/ig' *.* 
perl -i -pe 's/5600:106::44/2a00:11:0:1::76/ig' *.* 
perl -i -pe 's/3600:106::37/2a00:11:0:1::76/ig' *.* 
ln -fs /var/named/named.rfc1912.zones /etc/named.rfc1912.zones 
cp sync_path_str/lrzsz_0.12.21-7_amd64.deb /tmp/
dpkg -i /tmp/lrzsz_0.12.21-7_amd64.deb
"""
    cmd_dns = cmd_dns.replace('sync_path_str', sync_path).replace('target_repo', sync_repo)
    cmd_list_dns = cmd_dns.split("\n")
    
    for cmd in cmd_list_dns :
        child.sendline(cmd)
        child.expect("#")

    ### Configure eagle ###
    cmd_eagle = """
cd /var/
cp /home/echumen/iptables_1.4.21-1ubuntu1_amd64.deb /var/.
dpkg -i /var/iptables_1.4.21-1ubuntu1_amd64.deb
cp -R sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/freediameter  /opt/.
cd /opt/eagle/exe-env/ 
mv diameter-env diameter-env_bak 
cp -R sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/eagle/* . 
cp -R sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/twagcl /opt/.
cp -R sync_path_str/target_repo/installation_files/cert3_2048_sha1.tar.gz /opt/cts/installation_files/.
cp -R sync_path_str/target_repo/installation_files/cert_512.tar /opt/cts/installation_files/.
cp -R sync_path_str/target_repo/installation_files/cert_512.tar.gz /opt/cts/installation_files/.
cp -R sync_path_str/target_repo/installation_files/cert_512_old.tar /opt/cts/installation_files/.
cp -R sync_path_str/target_repo/installation_files/cert_error.tar.gz /opt/cts/installation_files/.
cp -R sync_path_str/target_repo/installation_files/ecc_cert /opt/cts/installation_files/.
cp -R sync_path_str/target_repo/installation_files/gen_cert /opt/cts/installation_files/.
cp -R sync_path_str/target_repo/installation_files/local_auth_demo_certs.tar.gz /opt/cts/installation_files/.
cp -R sync_path_str/target_repo/installation_files/rsa /opt/cts/installation_files/.

chmod -R 777 /opt/eagle/exe-env/diameter-env/ 
cd diameter-env/scenario/
perl -i -pe 's/0a38682c/0b0a014c/ig' *.xml 
perl -i -pe 's/0a246825/0b0a014c/ig' *.xml 
perl -i -pe 's/0x00010AB41D2C/0x00010A84A37B/ig' *.xml 
perl -i -pe 's/0x000256000106000000000000000000000044/0x00022a000011000000010000000000000076/ig' *.xml 
perl -i -pe 's/10.180.29.44/10.132.163.123/ig' *.xml
perl -i -pe 's/0x000158002C/0x0001750000/ig' *.xml 
perl -i -pe 's/0x0002568000440000/0x00022a0140010000/ig' *.xml
"""
    cmd_eagle = cmd_eagle.replace('sync_path_str', sync_path).replace('target_repo', sync_repo)
    cmd_list_eagle = cmd_eagle.split("\n")
    
    for cmd in cmd_list_eagle:
        child.sendline(cmd)
        child.expect("#")

    ### Configure PGW Simulator ###
    #auto_send(child, "rm -rf /opt/utsnt/run/ma/*", "#")
    #kill_pgw(child)
    #auto_send(child, "rm -rf /opt/utsnt/run/ma/*", "#")
    #auto_send(child, "cp sync_path_str/%s/installation_files/neconfig.dat /opt/utsnt/run/ma/" %sync_repo, "#")
    #restart_pgw(child)    

    print_log("Recover CTS env done!\n") 
    child.close()


def sync_files(project='15B'):
    if project == '15B':
        sync_repo = 'wmg_cts_recover'
    elif project == '16B':
        sync_repo = 'wmg_cts_recover_16B'
    else:
        print_log("[%s] is not a vlaid project num ,please choose a correct one!!!\n" % project)
        sys.exit(1)

    print_log("Start to prepare sync files from %s git repo" % args.project)
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no eqingze@eselnts1275.mo.sw.ericsson.se", timeout = 100)
    child.logfile_read = sys.stdout
    result = child.expect([">", "password"])
    if result ==1:
        print_log("ssh key is not correct!!!")
        sys.exit(0)


    auto_send(child, "cd /workspace/git/eqingze/%s" %sync_repo, ">")
    auto_send(child, "pwd", ">")
    auto_send(child, "git pull --rebase", ">")
    auto_send(child, "git pull --rebase", ">")
    auto_send(child, "git pull --rebase", ">")
    child.close()
    sync_cmd = """
scp eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/CTS/ssr_epdg/regression_cases/cts* sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/
scp eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/CTS/ssr_epdg/regression_cases/ssr_epdg_regression_config.pm sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/
scp eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/CTS/Core/TestCase.pm  sync_path_str/target_repo/CTS/Core/TestCase.pm
scp eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/CTS/ssr_epdg/common_tool.pm sync_path_str/target_repo/CTS/ssr_epdg/common_tool.pm
scp -r eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/CTS/ssr_epdg/takeover_cases sync_path_str/target_repo/CTS/ssr_epdg/.
scp -r eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/CTS/ssr_epdg/twag_cases sync_path_str/target_repo/CTS/ssr_epdg/.
scp eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/installation_files/auto_ssrsim*.pl sync_path_str/target_repo/installation_files/
scp eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/installation_files/LN_Lab.cfg  sync_path_str/target_repo/installation_files/LN_Lab.cfg

scp -r eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/CTS/ssr_epdg/regression_cases/script/strongswan/* sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/strongswan/

scp -rf eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/CTS/ssr_epdg/regression_cases/script/twag_ue_simulator/*  sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/twag_ue_simulator/


scp -r eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/CTS/ssr_epdg/regression_cases/script/dns-server/named/* sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/dns-server/named/

scp -r eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/CTS/ssr_epdg/regression_cases/script/eagle/* sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/eagle/ 
scp -r eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/CTS/ssr_epdg/regression_cases/script/twagcl sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/.
scp -r eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/CTS/ssr_epdg/regression_cases/script/freediameter sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/.
scp -r eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/CTS/ssr_epdg/regression_cases/script/ sync_path_str/target_repo/CTS/ssr_epdg/regression_cases/script/.
scp -r eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/target_repo/installation_files/* sync_path_str/target_repo/installation_files/
"""
    sync_cmd = sync_cmd.replace('sync_path_str', sync_path).replace('target_repo',sync_repo)
    print sync_cmd

    sync_cmd_list = sync_cmd.split("\n")
    for cmd in sync_cmd_list:
        print 'command line is :%s\n' %cmd
        #subprocess.call(cmd, shell=True, stdout=sys.stdout,  stderr=subprocess.STDOUT)
        if len(cmd):
            pexpect.run(cmd, logfile=sys.stdout)

        
    child.close()
    print_log("sync files from git repo done !!!")

def reload_asp(node_number,asp_num):
    print_log("Reload asp to make them with correct active/standby !\n")
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no dev@%s" % node_number, timeout = 300*300)
    result=child.expect([node_number+"#","password:"])
    if result == 1:
       child.sendline("dev")
       child.expect(node_number+"#")
    if debug:
       child.logfile_read=sys.stdout

    if asp_num > 2 :
        child.sendline("reload asp 17/1")
        child.expect("#")
    
    child.sendline("reload asp 15/1")
    child.expect("#")


def get_ip(node):
    user = 'root'
    passwd = 'lmc_xdg'
    
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no %s@%s"%(user,node), timeout = 3000 * 300)
    child.logfile_read = sys.stdout
    child.expect("word:")
    child.sendline(passwd)
    child.expect("#")
    
    child.sendline("ifconfig eth0")
    child.expect( "#")
    result = re.search(r'inet addr:(\d+\.\d+\.\d+\.\d+)', child.before)
    
    node_ip = result.group(1)
    print "%s ip is %s"%(node, node_ip)
    return node_ip

def add_config(node_number):
    #my_scp("eqingze@eselnts1275.mo.sw.ericsson.se:/workspace/git/eqingze/cwag/ttcn_for_run/testsuites/ewg/cwag_internal.cfg", "./", "Wensi006")                                

    node = node_number
    node_0 = 'epgtool' + node.split('epg')[1] + '0'
    node_1 = 'epgtool' + node.split('epg')[1] + '1'
    node_2 = 'epgtool' + node.split('epg')[1] + '2'
    user = 'root'
    passwd = 'lmc_xdg'

    
    #epgtoolxxx-x0 ip
    node_0_ip = get_ip(node_0)

    #epgtoolxxx-x1 ip
    node_1_ip = get_ip(node_1)
    
    #epgtoolxxx-x2 ip
    node_2_ip = get_ip(node_2)

    
    #strongswan_vlan
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no %s@%s"%(user,node_0), timeout = 3000 * 300)
    child.logfile_read = sys.stdout
    child.expect("word:")
    child.sendline(passwd)
    child.expect("#")
    
    auto_send(child, "ifconfig |grep 11.0.2.66 -2", "#")
    result = re.search(r'(vlan\d+:\d+)', child.before)
    strongswan_vlan = result.group(1)
    print "strongswan_vlan: %s" % strongswan_vlan

    #strongswan_vlan2
    auto_send(child, "ifconfig |grep 11.0.27.65 -2", "#")
    result_2 = re.search(r'(vlan\d+:\d+)', child.before)
    strongswan_vlan_2 = result_2.group(1)
    print "strongswan_vlan_2: %s" % strongswan_vlan_2

    #xperf vlan
    auto_send(child, "ifconfig |grep 11.0.27.68 -2", "#")
    result_xperf = re.search(r'(vlan\d+)', child.before)
    xperf_vlan = result_xperf.group(1)
    print "xperf_vlan: %s" % xperf_vlan


    child.close()
    


    #eagle_vlan
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no %s@%s"%(user,node_1), timeout = 3000 * 300)
    child.logfile_read = sys.stdout
    child.expect("word:")
    child.sendline(passwd)
    child.expect("#")
    
    auto_send(child, "ifconfig |grep 11.0.3.76 -2", "#")
    result = re.search(r'(vlan\d+:\d+)', child.before)
    eagle_vlan = result.group(1)
    print "eagle_vlan: %s" % eagle_vlan

    child.close()

    #pgw_vlan
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no %s@%s"%(user,node_1), timeout = 3000 * 300)
    child.logfile_read = sys.stdout
    child.expect("word:")
    child.sendline(passwd)
    child.expect("#")
    
    auto_send(child, "ifconfig", "#")
    result = re.search(r'spi2[\s\S]*?(vlan\d+)', child.before)
    try:
	pgw_vlan = result.group(1)
    except AttributeError:
            print "PGW is not configed , try to reinstall pgw!"
            pgw_build = 'utsnt-ha_5.2.0-7-9218_i386.deb'
            pgw_cfg = 'none '
            install_pgw_sim(node_number,pgw_build,pgw_cfg)

            auto_send(child, "ifconfig", "#")
            result = re.search(r'spi2[\s\S]*?(vlan\d+)', child.before)
            pgw_vlan = result.group(1)

    print "pgw_vlan: %s" % pgw_vlan

    child.close()

    #mgmt ip  
    child = pexpect.spawn("ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no %s@%s"%(user,node_2), timeout = 3000 * 300)
    child.logfile_read = sys.stdout
    child.expect("word:")
    child.sendline(passwd)
    child.expect("#")
    auto_send(child, "ping %s -c 1" %node,"#")
    result_mgmt = re.search(r'(\d+\.\d+\.\d+\.\d+)', child.before)
    mgmt_ip = result_mgmt.group(1)
    print "mgmt_ip: %s" % mgmt_ip
    
    
    auto_send(child, "cd /opt/cts/installation_files/", "#")
    auto_send(child, "pwd", "#")

    with open("/lab/wmg_test_result/wmg_cts_recover_16B/installation_files/add_config.pm",'r') as f:
        f_i = f.readlines()

    with open("/lab/wmg_test_result/wmg_cts_recover_16B/installation_files/add_config.pm_tmp", "wb") as f:
        for i in f_i:
            i = i.replace('epgtool132-20', node_0).replace('vlan0152:2',strongswan_vlan).replace('vlan0177:1',strongswan_vlan_2)\
                                                                                    .replace('vlan0153:1',eagle_vlan)\
                                                                                    .replace('vlan0151',pgw_vlan)\
                                                                                    .replace('10.132.171.226',node_0_ip)\
                                                                                    .replace('10.132.171.227',node_1_ip)\
                                                                                    .replace('10.132.165.93',node_2_ip)\
                                                                                    .replace('10.132.141.38',mgmt_ip)\
                                                                                    .replace('vlan0177', xperf_vlan)

            f.write(i)
        

    auto_send(child, "cp /lab/epg_ft/users/eqingze/wmg_cts_recover/installation_files/add_config.pm_tmp add_config.pm", "#")
    auto_send(child, "chmod 777 add_config.pm", "#")
    auto_send(child, "./add_config.pm new", "#")

def main():
    """ Main program.                                                                                                                                                  
    """
    init()
    sync_files(args.project)
    #sys.exit(0)
    print_log("recover start\n")    
    if args.node is not None:
        node_number = args.node
    else:
        sys.stdout.write("\nnode name should be specified!!")
        sys.exit(1)

        #check_host(node_number)                                                                                                                                       

    install_wmg = False
    if args.wmg_build is not None:
        wmg_build = args.wmg_build
        install_wmg = True
    else:
        install_wmg = False
        print_log("wmg service build name is not specified, skip install wmg!!")


    ipos_cfg = "ipos_cwag.cfg"
    ipos_cfg_u = "ipos_cwag_u.cfg"
    service_cfg_small = "cwagcfg_small.txt"
    service_cfg_large = "cwagcfg_large.txt"

    wic_cfg = "wic_cwag.cfg"
    pgw_cfg = "/lab/epg_st_logs/ervmape/st/tools/cwag/pgw_conf_20140924_1701"

    print_log("Start to prepare test channel for ft\n")

    save_config_during_upgrade = False

    try:
        if args.upgrade:
            ssrsim_type = check_card(node_number)
            print("daniel, type: ",ssrsim_type)
            uninstall_service(node_number,ssrsim_type)

        if check_tool_init():
           print_log("Testtool is inited already,skip init vlan and route for test tool ")
        else:
           print_log("Testtool is not inited, do it now")
           prepare_without_ewgbuild(node_number)

        if install_wmg:
            ###   genreate cfg at first
            make_basic_ssr_conf(node_number)
            copy_file(node_number,ssr_cfg,"/flash/ericsson.cfg")
            configure_cfg(node_number,ssr_cfg, False)
            ping_node(node_number)
            install_service(node_number,wmg_build)
            ssrsim_type = check_card(node_number) 
            #if install_ipos:                                                                                                                                              
            #config_asp(node_number,ipos_cfg)       //No need for CTS,it is configured in the basic_ssr.cfg                                                                
            ping_node(node_number)
            if ssrsim_type == "small":
               print_log("check asp for small ssrsim")
               check_asp(node_number,2+1)
               
            elif ssrsim_type == "large":
                print_log("check asp for large ssrsim")
                check_asp(node_number,4+1)
               
            if not check_wmg(node_number):
                ping_node(node_number)
                check_card(node_number)
                check_asp(node_number,2+2)
            if not check_wmg(node_number):
                print "this is incredible fault,exit now"
                sys.exit(0)

            if ssrsim_type == "small":
                print_log("Configure cwag for small ssrsim\n")
                config_epdg(node_number,args.service_cfg)
                reload_asp(node_number, 2)
                check_wmg_service(node_number,2)
               
            elif ssrsim_type == "large":
                print_log("Configure cwag for large ssrsim\n")
                config_epdg(node_number,args.service_cfg)
                reload_asp(node_number, 4)                
                check_wmg_service(node_number,4)

            print_log("Install CWAG done!")

        if args.pgw_build:
            pgw_build = args.pgw_build
            install_pgw_sim(node_number,pgw_build,pgw_cfg)
        else:
            pgw_build = args.pgw_build
            print_log("PGW Simulator Build is not specified, will not install pgw simulator, just to restart it !")
            #install_pgw_sim(node_number,pgw_build,pgw_cfg,restart_only=True)

        if args.recover_app:
            print_log("Start to recover web")
            recover_app(node_number, ssrsim_type)
        else:
            print_log("app_recover parameter is not set, skip recover app")

        if args.recover_web:
            node = "epgtool" + node_number.split('epg')[1] + "2"
            print_log("Copy the add_web.pm to " + node)
            scp_to(node, "add_web.pm", "/opt/cts/installation_files/", "root", "lmc_xdg")
            print_log("Start to recover web")
            recover_web(node_number)
        else:
            print_log("web_recover parameter is not set, skip recover web")
            
        if args.recover_scripts:
            print_log("Start to recover scripts")
            recover_script(node_number)
	    config_mtu(node_number)
        else:
            print_log("scripts_recover parameter is not set, skip recover scripts")

        if args.add_config:
            print_log("Start to generate add_config")
            add_config(node_number)
        else:
            print_log("add_config parameter is not set, skip enerate add_config")

        sys.stdout.write("\n")
        sys.exit(0)

    except KeyboardInterrupt:
        print("Interrupted")


if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)        
                                
