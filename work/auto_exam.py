# coding:utf-8

import os
import random
import configparser

with open('province.txt', 'r') as f:
    province_data = f.readlines()

config = configparser.ConfigParser()
with open('province_capital.txt', 'r') as cfg:
    config.readfp(cfg)
    provinces = config.sections()
    province_capitals = {}
    for i in range(provinces.__len__()):
        province_capitals[provinces[i]] = config.get(provinces[i], 'city')
    print(province_capitals)


    #for i in range(config.__len__()):

def generate_exam(n):
    for i in range(1, n + 1):
        province = provinces[random.randint(0, provinces.__len__())]
        print('% s . 以下哪个城市是 % s 的省会？' % (i, province))
        #print('A. % s' % )

name = config.get('河北省', 'city')


if __name__ == '__main__':
    generate_exam(3)
