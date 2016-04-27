#!/lab/gw_test_framework/app/venv/python3.5-rhes6.x86_64-epglib2/bin/python
#  coding:utf-8



import os
import datetime
import pexpect
import subprocess
import sys

def clean_file(file_dir, days=15):
    lists = os.listdir(file_dir)
    file_lists = []
    count = 0
    for i in range(len(lists)):
        path = os.path.join(file_dir, lists[i])
        if os.path.isfile(path):
            if lists[i] != r'*':
                file_lists.append(lists[i])

    for i in range(len(file_lists)):
        path = os.path.join(file_dir, file_lists[i])
        if os.path.isdir(path):
            continue
        timestamp = os.path.getmtime(path)
        file_date = datetime.datetime.fromtimestamp(timestamp)
        now = datetime.datetime.now()
        if (now - file_date) > datetime.timedelta(days=days):
            print('file date is: % s' % file_date)
            print('removing: % s' % path)
            os.remove(path)
            count = count + 1
        else:
            print('file % s is safe' % file_lists[i])

    print('total % s files are deleted.' % count)

def auto_send(child, cmd, response):
    child.sendline(cmd)
    child.expect(response)

def clean_all(server, file_dir):
    _password = '123qweasdZXC6'
    _cmd = 'ssh -q -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ForwardX11=no epstuac@' + server
    print('start to connect to server % s!' % server)
    try:
        child = pexpect.spawn(_cmd, timeout=10)
        result = child.expect(['>', 'password:'])
        if result == 1:
            child.sendline(_password)
            print('login server with password successfully!')
        elif result == 0:
            print('login server without password successfully!')
        auto_send(child, r'cd' + file_dir, '>')
        auto_send(child, r'rm -rf ./pre_load/wmg*', '>')
        auto_send(child, r'ls -lrt ./pre_load/', '>')
        auto_send(child, r'rm -rf ./pre_load2/wmg*', '>')
        auto_send(child, r'ls -lrt ./pre_load2/', '>')
        auto_send(child, r'rm -rf ./pre_load3/wmg*', '>')
        auto_send(child, r'ls -lrt ./pre_load3/', '>')
        auto_send(child, r'rm -rf ./pre_load4/wmg*', '>')
        auto_send(child, r'ls -lrt ./pre_load4/', '>')
        child.close()
    except pexpect.EOF:
        print('EOF')
        child.close()
    except pexpect.TIMEOUT:
        print('connect to server TIMEOUT!')
        child.close()

def sync_file(sync_way, file_dir):
    if sync_way == 'to1001':
        sync_cmd = '/lab/gw_test_framework/epglib2/bin/lab_storage_sync sync -s SERO -d SELN ' + file_dir
        retcode = subprocess.call(sync_cmd, shell=True, stdout=open('/dev/null', 'w'), stderr=subprocess.STDOUT)
        if retcode == 1:
            print('sync fail!!!')
            sys.exit()
    elif sync_way == 'to1275':
        sync_cmd = '/lab/gw_test_framework/epglib2/bin/lab_storage_sync sync -s SERO -d SELN ' + file_dir
        retcode = subprocess.call(sync_cmd, shell=True, stdout=open('/dev/null', 'w'), stderr=subprocess.STDOUT)
        if retcode == 1:
            print('sync fail!!!')
            sys.exit()




if __name__ == '__main__':
    file_dir = input('please input the path:')
    days = int(input('please input the days:'))
    clean_file(file_dir, days)
