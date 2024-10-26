import time
from datetime import datetime, timedelta
from utils.logger import logger,Logger
from Venue import NkuVenue
import multiprocessing
import argparse,json, random

def _wait_time_is_num(wait_seconds, lg=None):
        if wait_seconds > 3600: 
            interval = 30 * 60
        elif wait_seconds > 600: 
            interval = 5 * 60
        elif wait_seconds > 60: 
            interval = 30
        elif wait_seconds > 10: 
            interval = 5
        else: 
            interval = 0.5
        
        if lg:
            lg.info(
                f"Waiting for {int(wait_seconds // 3600)} hours, "
                f"{int((wait_seconds % 3600) // 60)} minutes, "
                f"and {int(wait_seconds % 60)} seconds, "
                f"sleep in {interval} seconds."
            )
        return interval
    

def wait_until_time(agent, schedule_time, log_name, state_dict,message_dict, **kwargs):

    hour, minute, second = schedule_time
    lg = Logger(log_name)

    while True:
        now = datetime.now()
        target_time = now.replace(hour=hour, minute=minute, second=second, microsecond=0)

        if now > target_time:
            target_time += timedelta(days=1)

        wait_seconds = (target_time - now).total_seconds()
        interval = _wait_time_is_num(wait_seconds, lg)
        
        if abs(wait_seconds) < 0.5:
            
            for i in range(4):
                ret, mess = agent.rub(**kwargs, logger=lg)
                message_dict[log_name] = mess

                if ret:
                    break
                time.sleep(3)
            state_dict[log_name] = True
            return

        time.sleep(interval)


if __name__ == '__main__':
    # python main.py --user_id  --password  --venue_no 4 5 6 7 --time 15 16 --workers_num 5
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--user_id', type=str, default='2111252', help='学号')
    parser.add_argument('--password', type=str, default='', help='密码')
    parser.add_argument('--venue_no', type=int, default=[4,5,6,7], help='你想订的场地编号')
    parser.add_argument('--time', nargs='+', type=int, default=[19, 20], help='订的时间')
    parser.add_argument('--workers_num', type=int, default=1, help='工作进程数量')
    
    # 这里固定就好
    parser.add_argument('--schedule_time', nargs=3, type=int, default=[12, 0, 1], help='(时 分 秒)')
    parser.add_argument('--dateadd', type=int, default=3, help='(0-3)')
    parser.add_argument('--price', type=int, default=10, help='价格')
    args = parser.parse_args()
    
    username = args.user_id
    password = args.password
    venue_no_list = args.venue_no
    atime = args.time
    price = args.price
    schedule_time = tuple(args.schedule_time)
    #schedule_time = datetime.now().hour, datetime.now().minute, datetime.now().second+10
    workers_num = args.workers_num
    dateadd = args.dateadd


    checkData_template = (
                f'[{{"FieldNo": "JNYMQ0{str(venue_no_list[0]).zfill(2)}", "FieldTypeNo": "JNYMQ", "FieldName": "羽{str(venue_no_list[0]).zfill(2)}", "BeginTime": "{atime[0]}:00", "Endtime": "{atime[0]+1}:00", "Price": "{price}.00"}},'
                f' {{"FieldNo": "JNYMQ0{str(venue_no_list[0]).zfill(2)}", "FieldTypeNo": "JNYMQ", "FieldName": "羽{str(venue_no_list[0]).zfill(2)}", "BeginTime": "{atime[1]}:00", "Endtime": "{atime[1]+1}:00", "Price": "{price}.00"}}]'
                )
    logger.info(f'\n\tusername: {username}, \n\thash password: {password}, \n\t选择的场地编号: {venue_no_list}, \n\t选择的时间段: {atime},\n\tworkers_num: {workers_num}')
    logger.info(f'checkData: \n{checkData_template}')
    
    agent = NkuVenue(username, password, logger)
    
    # agent.report_free_venues()
    # agent.rub(checkData,dateadd)
    
    processes = []
    manager = multiprocessing.Manager()
    status_dict = manager.dict()
    
    order_success_dict = manager.dict()
    
    while True:
        hour, minute, second = schedule_time
        now = datetime.now()
        target_time = now.replace(hour=hour, minute=minute, second=second, microsecond=0)

        if now > target_time:
            target_time += timedelta(days=1)
        wait_seconds = (target_time - now).total_seconds()
        interval = _wait_time_is_num(wait_seconds, logger)
        
        if wait_seconds  < 55:
            agent._update_cookie()
            break
        time.sleep(interval)

    ## 开启线程准备
    import random
    for i in range(workers_num):
        
        log_name = f'thread-{i}'
        status_dict[log_name] = False
        order_success_dict[log_name] = {}
        
        # venue_no = str(random.randint(4, 5))
        venue_no = str(random.choice(venue_no_list))
        checkData = []
        for t in atime:
            checkData.append({
                              "FieldNo":        f"JNYMQ0{str(venue_no).zfill(2)}", 
                              "FieldTypeNo":    "JNYMQ",
                              "FieldName":      f"羽{str(venue_no).zfill(2)}",
                              "BeginTime":      f"{t}:00", 
                              "Endtime":        f"{t+1}:00", 
                              "Price":          f"{price}.00"    # 这个好像可以随便填
                              })

        p = multiprocessing.Process(
                                    target=wait_until_time, 
                                    args=(agent, schedule_time, log_name,status_dict,order_success_dict), 
                                    kwargs={'checkData':json.dumps(checkData, ensure_ascii=True), 'dateadd':dateadd}
                                    )
        p.start()
        processes.append(p)
        time.sleep(random.randint(10, 20) / 10.0)

    while not all(status_dict.values()):
        time.sleep(1)

    for i in range(workers_num):
        log_name = f'thread-{i}'
        if order_success_dict[log_name].__len__() and order_success_dict[log_name].get('paying_link'):
            logger.info(f'{log_name} 订场成功: {order_success_dict[log_name]}, pay link: {order_success_dict[log_name]["paying_link"]}')
            # agent.send_report_to_wechat(f'订场成功， pay link: {order_success_dict[log_name]["paying_link"]}')
            
            break

    
    logger.info(f'{log_name} 订场失败')
    # agent.send_report_to_wechat(f'订场失败')
    
    for p in processes:
        p.join()

    print('exit 0')



