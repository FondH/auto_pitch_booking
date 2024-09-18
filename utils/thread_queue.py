import queue
import threading
import time
import datetime
from queue import Queue


def thread_task(task_id, result_queue, task_func, *task_args, **task_kwargs):
    """
    执行任务的线程函数。如果任务成功，向队列中放入结果。
    """
    try:
        #print(f"Thread {task_id} started.")

        result = task_func(*task_args, **task_kwargs)
        if isinstance(result, str):
            # 将任务结果放入队列中
            result_queue.put((task_id, result))
            print(f"Thread {task_id} completed successfully with result: {result}")
    except Exception as e:
        print(f"Thread {task_id} encountered an error: {e}")


def thread_schedule_push(scheduled_time, task_func, *task_args, **task_kwargs):
    # scheduled_time :
    """

    :param scheduled_time (str): 12:00
    :param task_func:
    :param task_args:
    :param task_kwargs:
    :return: {'status':'completed', 'result':}
             {'status':'error', 'result':}
    """

    max_thread = 5
    if  scheduled_time:

        # 计算距离计划时间的秒数
        now = datetime.datetime.now()
        scheduled_time = datetime.datetime.strptime(scheduled_time, "%H:%M").replace(year=now.year, month=now.month,
                                                                                         day=now.day)
        if scheduled_time < now:
            print('the schedule time is history')
            return

        wait_seconds = (scheduled_time - now).total_seconds()

        if wait_seconds > 0:
            print(f"Waiting for {wait_seconds} seconds until the scheduled time...")
            time.sleep(wait_seconds)

    else:
        print("no schedule time,Waiting for 3 seconds until...")
        time.sleep(1)

    # 任务队列，用于线程间通信
    result_queue = Queue()
    threads = []

    for i in range(max_thread):
        t = threading.Thread(target=thread_task, args=(i, result_queue, task_func) + task_args, kwargs=task_kwargs)
        threads.append(t)
        t.start()
        time.sleep(0.5)

    # 等待任意一个线程成功完成任务
    rs = {}
    try:
        task_id, result = result_queue.get(timeout=15)
        rs['status'] = 'completed'
        rs['result'] = result

        print(f"success signal from thread {task_id} with result: {result}")

    except TimeoutError:
        rs['status'] = 'error'
        rs['result'] = 'TimeoutError'
        print(f"defeat signal")

    except queue.Empty:
        rs['status'] = 'error'
        rs['result'] = 'defeat'
        print(f"queue empty signal")

    finally:
        # 终止所有线程
        for t in threads:
            if t.is_alive():
                t.join(timeout=1)

    return rs


def sample_task(x, y):
    """
    示例任务函数：执行一些计算任务
    """
    print(f"Executing task with arguments: {x}, {y}")
    time.sleep(2)  # 模拟任务执行时间
    if x + y == 5:  # 假设这个条件表示任务成功
        return "Success"
    else:
        raise Exception("Task failed")


if __name__ == "__main__":
    # 设定计划时间
    scheduled_time = datetime.datetime.now() + datetime.timedelta(seconds=10)  # 10秒后执行
    result = thread_schedule_push(scheduled_time, sample_task, 2, 3)  # 传递任务函数及其参数
    print(f"Main function returned with result: {result}")
