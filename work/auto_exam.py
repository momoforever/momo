# coding:utf-8

import os
import random
import configparser

config = configparser.ConfigParser()
with open('province_capital.txt', 'r') as cfg:
    config.readfp(cfg)
    provinces = config.sections()
    province_capitals = {}
    for i in range(provinces.__len__()):
        province_capitals[provinces[i]] = config.get(provinces[i], 'city')
    citys = list(province_capitals.values())

def generate_exam(n):
    for i in range(1, n + 1):
        province = provinces[random.randint(0, provinces.__len__()-1)]
        print('% s . 以下哪个城市是 % s 的省会？' % (i, province))
        answers = random.sample(citys, 4)
        for j in range(4):
            match = 0
            if answers[j] == config.get(province, 'city'):
                match = match + 1
        if match < 1:
            answers[random.randint(0, 3)] = config.get(province, 'city')
        print('A. % s' % answers[0])
        print('B. % s' % answers[1])
        print('C. % s' % answers[2])
        print('D. % s' % answers[3])

if __name__ == '__main__':
    generate_exam(28)
