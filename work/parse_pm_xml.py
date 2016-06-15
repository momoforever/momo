#!/lab/gw_test_framework/app/venv/python3.5-rhes6.x86_64-epglib2/bin/python
#  coding:utf-8
#
#    Author: Dream Liu
#    Version: 1.0
#


import sys
import gzip
import xml.etree.ElementTree as ET
import re
from collections import Counter

def GetPmHash(pm_file):
    name_space = r'<measCollecFile xmlns=[\s\S]+?>'
    
    f = gzip.open(pm_file, 'rb')
    file_content = f.read()

    #remove the name space to make it easy
    match = re.search(name_space, file_content).group(0)



    if match:
        file_content = file_content.replace(match, '<measCollecFile>')
    else:
        print "Error: name_space is changed, please modify this script!!!"
        sys.exit()
        

    #Get the root element of the xml file
    root = ET.fromstring(file_content)




    meas_info_list = []
    #meas_type_list = []
    meas_value_list = []
    meas_total_dict = {}
    num_NomeasObjLdn = 0

    #Get the parent element
    for meas_info in root.iter(tag= 'measInfo'):
        meas_info_list.append(meas_info)

    #Under the parent element, get the brother elements
    for child in meas_info_list:
        meas_type_list = []
        for child_child  in child.iter(tag= 'measValue'):
            meas_value_list.append( child_child.attrib.keys()[0] + ' : ' + child_child.attrib['measObjLdn'] )

        for child_child  in child.iter(tag= 'measType'):
            meas_type_list.append(child_child.text)

        try:
            meas_total_dict[meas_value_list.pop()] = meas_type_list
        except IndexError, msg:
            #print "IndexError due to %s! make the measObjLdn to be NomeasObjLdn!" % msg[0]
            num_NomeasObjLdn = num_NomeasObjLdn + 1
            #meas_total_dict['NomeasObjLdn_' + str(num_NomeasObjLdn)] = meas_type_list
            meas_total_dict[num_NomeasObjLdn] = meas_type_list

                    
    f.close()
    return meas_total_dict

def CompareHash(last_hash_table, new_hash_table):
    #    print last_hash_table
    #print new_hash_table

    for key in last_hash_table.keys():
        try:
            if last_hash_table[key] != new_hash_table[key]:
                print "Same key, different values:"
                print "key is: %s" % key
                print "last_hash_table: "
                #print "key: " +  key
                print "values:" 
                print last_hash_table[key]
                print "\n"

                print "new_hash_table: "
                #print "key: " +  key
                print "values:" 
                print new_hash_table[key]
                print "*********************************************************"

        except KeyError:
            print "key : %s is  at last_hash_table, not at new_hash_table" % key
            print "*********************************************************"
            
            
    for key in new_hash_table.keys():
        try:
            last_hash_table[key]
        except KeyError:
            print "key : %s is  at last_hash_table, not at last_hash_table" % key
            print "*********************************************************"
                
            
    
    
def main():

    try:        
        if sys.argv[1] == '--help':
            print "this script is to compare 2 pm files. Example: parse_pm_xml.py $last_release_file $new_release_file"

        else:
            last_release = sys.argv[1]#'pm_sample.xml.gz'
            new_release = sys.argv[2]#'185_xml.gz'

            last_hash = GetPmHash(last_release)
            new_hash = GetPmHash(new_release)
            
            CompareHash(last_hash, new_hash)


    except IndexError:
            print "another pm file is required!!!"
    

    
    #print last_hash
    #print new_hash

if __name__ == '__main__':
    main()

