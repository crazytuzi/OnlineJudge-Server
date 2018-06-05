#!/usr/bin/env python
# coding=utf-8
import os
import logging
import sys
import threading
import time
import config
import _judger
import redis
import os
import os.path
from Queue import Queue
def low_level():
    try:
        # 降低程序运行权限，防止恶意代码
        # os.setuid(uid) 设置当前user id
        # os.popen() 方法用于从一个命令打开一个管道
        # 在Linux下，目录权限一般为755，也就是说，如果换成一个别的用户，只要不是所有者，就没有修改和删除的权限。
        # python里面可以使用os.setuid(int(os.popen("id -u %s"%"nobody").read()))来将程序以nobody用户的身份执行
        os.setuid(int(os.popen("id -u %s" % "nobody").read()))
    except:
        logging.error("please run this program as root!")
        sys.exit(-1)


# Redis 的连接池是多线程安全的、多进程安全的、自动重连的
'''
通常情况下, 当我们需要做redis操作时, 会创建一个连接, 并基于这个连接进行redis操作, 操作完成后, 释放连接,

一般情况下, 这是没问题的, 但当并发量比较高的时候, 频繁的连接创建和释放对性能会有较高的影响

于是, 连接池就发挥作用了

连接池的原理是, 通过预先创建多个连接, 当进行redis操作时, 直接获取已经创建的连接进行操作, 
而且操作完成后, 不会释放, 用于后续的其他redis操作

这样就达到了避免频繁的redis连接创建和释放的目的, 从而提高性能了
'''
def redis_conn(host='localhost',port=6379,password='',db=0):
    pool=redis.ConnectionPool(host=host,port=port,password=password,db=db,decode_responses=True)
    return redis.Redis(connection_pool=pool)

# 初始化队列
q = Queue(config.count_thread)
# 初始化连接池
redis_0=redis_conn(host=config.redis_host,port=config.redis_port,password=config.redis_password,db=0)
redis_1=redis_conn(host=config.redis_host,port=config.redis_port,password=config.redis_password,db=1)
redis_2=redis_conn(host=config.redis_host,port=config.redis_port,password=config.redis_password,db=2)
redis_3=redis_conn(host=config.redis_host,port=config.redis_port,password=config.redis_password,db=3)
redis_4=redis_conn(host=config.redis_host,port=config.redis_port,password=config.redis_password,db=4)
redis_5=redis_conn(host=config.redis_host,port=config.redis_port,password=config.redis_password,db=5)

# 返回锁对象。用于生成原始锁对象的工厂函数。
# 一旦某个线程获得了这个锁，其他的线程要想获得他就必须阻塞，直到锁被释放。
redis_lock = threading.Lock()

def start_work_thread():
    # 开启工作线程
    for i in range(config.count_thread):
        # 第一个参数是线程函数变量，第二个参数args是一个数组变量参数，
        # 如果只传递一个值，就只需要i,
        # 如果需要传递多个参数，那么还可以继续传递下去其他的参数，
        # 其中的逗号不能少，少了就不是数组了，就会出错。
        t = threading.Thread(target=work)
        # 设置为daemon的线程会随着主线程的退出而结束，而非daemon线程会阻塞主线程的退出。
        t.deamon = True
        t.start()


def put_task_into_queue():
    # 循环扫描数据库,将任务添加到队列
    while True:
        # Queue.join() 实际上意味着等到队列为空，再执行别的操作
        q.join() # 阻塞程序,直到队列里面的任务全部完成
        #执行数据库操作
        keys=redis_0.keys()
        time.sleep(0.2)
        for key in keys:
            conf=redis_0.hgetall(key)
            print(conf)
            status = conf['status']
            if status == '0':
                runid=str(key)
                problemid=conf['problemid']
                code = conf['code']
                username= conf['username']
                TimeLimit = int(conf['TimeLimit'])
                MemoryLimit = int(conf['MemoryLimit'])
                redis_lock.acquire()
                runfile_name_conf=config.code_path+runid
                runfile_name=config.code_path+runid+'.c'
                outputfile_name = config.temp_path+runid + config.file_extension
                errorfile_name = config.temp_path+runid + config.file_extension
                os.mknod(runfile_name)
                file = open(runfile_name, 'w')
                file.write(code)
                file.close()
                redis_lock.release()
                task = {
                    "runid": runid,
                    "problemid": problemid,
                    "username":username,
                    "TimeLimit": TimeLimit,
                    "MemoryLimit": MemoryLimit,
                    "runfile_name_conf":runfile_name_conf,
                    "outputfile_name":outputfile_name,
                    "errorfile_name":errorfile_name,
                }
                q.put(task)
                redis_lock.acquire()
                redis_0.delete(key)
                redis_lock.release()
        time.sleep(0.5)

def start_get_task():
    # 开启获取任务线程
    t = threading.Thread(target=put_task_into_queue,name='get_task')
    t.deamon = True
    t.start()

def check_thread():
    #low_level()
    # 检查评测程序是否存在,小于config规定数目则启动新的
    while True:
        try:
            if threading.active_count() < config.count_thread + 2:
                logging.info("start new thread")
                t = threading.Thread(target=work)
                t.deamon = True
                t.start()
            time.sleep(1)
        except:
            pass

def start_protect():
    # 开启守护进程
    # low_level()
    t = threading.Thread(target=check_thread,name='check_thread')
    t.daemon = True
    t.start()





def work():
    # 工作线程，循环扫描队列，获得评判任务并执行
    while True:
        if q.empty() is True: # 队列为空，空闲
            logging.info("%s idle" % (threading.current_thread().name))
        task = q.get() # 获取任务，如果队列为空则阻塞
        runid=task["runid"]
        problemid = task["problemid"]
        username = task["username"]
        TimeLimit = task["TimeLimit"]
        MemoryLimit = task["MemoryLimit"]
        runfile_name_conf = task["runfile_name_conf"]
        outputfile_name = task["outputfile_name"]
        errorfile_name = task["errorfile_name"]
        result, cpu_time, memory = judge(problemid, runfile_name_conf, outputfile_name, errorfile_name, TimeLimit,
                                         MemoryLimit) # 评判
        redis_lock.acquire()
        # 将结果写入数据库
        redis_3.hset(runid,'result',result)
        redis_3.hset(runid,'run-time',cpu_time)
        redis_3.hset(runid,'run-memory',memory)
        hresult=redis_2.hgetall(problemid)
        result_count=hresult[config.result_list[result+1]]
        redis_2.hset(problemid,config.result_list[result+1],int(result_count)+1)
        if result == 0:
            redis_4.sadd(username,problemid)
            redis_5.srem(username,problemid)
        else:
            members = redis_4.smembers(username)
            if problemid not in members:
                redis_5.sadd(username,problemid)
        redis_lock.release()
        if config.auto_clean:# 清理work目录
            pass
        q.task_done() # 一个任务完成

def run(file_path_conf='',input_path_conf='',answer_path_conf='',output_path_conf='',error_path_conf='',
        max_cpu_time_conf=1000,max_memory_conf=128):
    ret = _judger.run(max_cpu_time=max_cpu_time_conf,
                      max_real_time=max_cpu_time_conf*2,
                      max_memory=max_memory_conf * 1024 * 1024,
                      max_process_number=200,
                      max_output_size=10000,
                      max_stack=32 * 1024 * 1024,
                      # five args above can be _judger.UNLIMITED
                      exe_path=file_path_conf,
                      input_path=input_path_conf,
                      output_path=output_path_conf,
                      error_path=error_path_conf,
                      answer_path=answer_path_conf,
                      args=[],
                      # can be empty list
                      env=[],
                      log_path="judger.log",
                      # can be None
                      seccomp_rule_name="c_cpp",
                      uid=0,
                      gid=0)
    return ret

def judge(problemid,runfile_name,outputfile_name,errorfile_name,max_cpu_time,max_memory):
    gcc_eval="gcc "+runfile_name+'.c'+" -o "+runfile_name
    if os.system(gcc_eval):
        return 8,0,0
    path=config.problem_path+str(problemid)
    file_list=os.listdir(path)
    file_count=len(file_list)/2
    max_cpu_time_use=-1
    max_memory_use=-1
    for i in range(file_count):
        in_path=os.path.join(path,'%d.in'%i)
        out_path=os.path.join(path,'%d.out'%i)
        if os.path.isfile(in_path) and os.path.isfile(out_path):
            ret=run(file_path_conf=runfile_name,input_path_conf=in_path,answer_path_conf=out_path,
                    output_path_conf=outputfile_name,error_path_conf=errorfile_name,
                    max_cpu_time_conf=max_cpu_time,max_memory_conf=max_memory)
            print(ret)
            result=ret['result']
            cpu_time = ret['cpu_time']
            memory = ret['memory']
            if result == 0:
                if cpu_time > max_cpu_time_use:
                    max_cpu_time_use=cpu_time
                if memory >max_memory_use:
                    max_memory_use=memory
            else:
                return result,cpu_time,memory
        else:
            pass
    return 0,max_cpu_time_use,max_memory


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s --- %(message)s',
    )
    start_get_task()
    start_work_thread()
    start_protect()

def test():
    problemid = u'1'
    runfile_name = '/oj/code/10'
    outputfile_name = '/oj/temp/10.output'
    errorfile_name = '/oj/temp/10.output'
    max_cpu_time = 256
    max_memory = 1000
    result, cpu_time, memory = judge(problemid, runfile_name, outputfile_name, errorfile_name, max_cpu_time, max_memory)

if __name__ == '__main__':
    main()
