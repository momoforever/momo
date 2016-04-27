#!/lab/gw_test_framework/app/venv/python3.5-rhes6.x86_64-epglib2/bin/python
#  coding:utf-8


import os
import datetime

def clean_file(file_dir, days):
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
            print('file % s is safe' % path)

    print('total % s files are deleted.' % count)


if __name__ == '__main__':
    file_dir = input('please input the path:')
    days = int(input('please input the days:'))
    clean_file(file_dir, days)
