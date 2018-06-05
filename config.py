#!/usr/bin/env python
#coding=utf-8
#开启评测线程数目
count_thread = 4
#评测程序队列容量
#数据库地址
redis_host="localhost"
#数据库端口号
redis_port=6379
#数据库密码
redis_password="olily"
#problem目录
problem_path="/oj/problem/"
#code目录
code_path="/oj/code/"
#temp目录
temp_path="/oj/temp/"
#文件后缀
file_extension=".output"
#自动清理评work目录
auto_clean = True
#WA -1 0
#AC 0 1
result_list=[
    'WA',
    'AC',
    'TLE',
    'RTLE',
    'MLE',
    'RE',
    'SE',
    'PE',
    'OLE',
    'CE',

]