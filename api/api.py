"""
    api.py 为flask的web界面提供底层支持，即web.py 需要调用
"""

import os,time,json
import requests
import datetime
import pandas as pd

def get_hearder():
    return {
        'Host': 'tycgs.nankai.edu.cn',
        'Connection': 'keep-alive',
        'Cache-Control': 'no - cache',
        'Accept': '*/*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en,zh-CN;q=0.9,zh;q=0.8'
    }

def get_tp():
    return int(time.time()*1000)


def tp2str(timestamp):

    timestamp = timestamp / 1000
    dt_object = datetime.datetime.fromtimestamp(timestamp)

     # 输出格式为 YYYY-MM-DD
    return  dt_object.strftime('%Y-%m-%d %H:%M:%S') + '.{:03d}'.format(int(dt_object.microsecond / 1000))

def get_all_list(cookie, days):
    """

    :param cookie:
    :return: {0:[{},{}], 1:[{},{}] }
    """
    # dateadd 0-3 表示今天、明天、后天、大后天（可以无）


    print(f'get_all_list: refresh field data')
    _url = 'http://tycgs.nankai.edu.cn/Field/GetVenueStateNew?dateadd={}&TimePeriod={}&VenueNo=003&FieldTypeNo=JNYMQ&_={}'
    status = {}
    for i in days:
        day_data = []
        for period in range(3):
            tar_u = _url.format(i, period,get_tp())
            #print(tar_u)
            try:

                rs = requests.get(tar_u,headers=get_hearder(),cookies=cookie)
                rs.raise_for_status()

                if rs:
                    json_data = dict(rs.json())
                    if isinstance(json_data['resultdata'], str):
                        result_data = json.loads(json_data['resultdata'])
                    else:
                        result_data = json_data['resultdata']

                    day_data += result_data
                    time.sleep(0.2)

            except Exception as e:
                pass

            status[i] = day_data

    return status

def get_all_pds(cookie, days, Test=False):
    """

    :param cookie:
    :param days:
    :return:  {0:pd, 1:pd}
    """

    if not isinstance(days, list):
        days = [days]

    if Test:
        status = get_test_data()
        df = pd.DataFrame(status[0])
        df['AvailableForRent'] = (df['FieldState'] == '1').map(
            {True: 'Available', False: 'Not Available'})


        return { 0 : df[
                ['FieldName', 'BeginTime', 'EndTime', 'FieldNo', 'FinalPrice', 'FieldTypeNo', 'FieldState', 'TimeStatus',
                'AvailableForRent']]
                }

    else:
        status = get_all_list(cookie,days)


    dfs = {}
    for ind, sta in status.items():
        df = pd.DataFrame(sta)
        try:
            # 根据BeginTime和EndTime排序
            df.sort_values(by=['BeginTime', 'EndTime'], inplace=True)
            df['AvailableForRent'] = ((df['FieldState'] == '0') & (df['TimeStatus'] == '1')).map(
                {True: 'Available', False: 'Not Available'})

            df = df[
                ['FieldName', 'BeginTime', 'EndTime', 'FieldNo', 'FinalPrice', 'FieldTypeNo', 'FieldState', 'TimeStatus','AvailableForRent']]
            dfs[ind] = df
        except:
            print(f"fetch field data from remote Error, Please Check the 'uid' and 'jwt' ({sta[:30]})")
            print(df.head())


    return dfs



def get_available(df):
    """
    tp (5-1(week1), df)
    """

    available_fields = df[df['AvailableForRent'] == 'Available']
    #print(f"{df[0]} has total Available Fields: { available_fields.shape[0]}")
    return available_fields

def get_all_available(dfs):
    """
    :param: avai_dfs {0:pd,1:pd}
    """
    avai_dfs = {}
    for i, df in dfs.items():
        avai_dfs[i] = get_available(df)

    return avai_dfs

def unicode_to_ascii_bytes(chinese_str):
    ascii_list = []
    for char in chinese_str:
        # 将字符编码为 UTF-8 字节 然后转换为换为对应的 ASCII 字符表示
        ascii_bytes = [chr(byte) for byte in char.encode('utf-8')]
        ascii_list.extend(ascii_bytes)

    return ''.join(ascii_list)
def get_checkdata(entrys):
    checkdata = []

    if not isinstance(entrys, list):
        entrys = [entrys]

    for entry in entrys:
        entry = entry.iloc[0]
        fildNo = entry['FieldNo']
        fieldTypeNo = entry['FieldTypeNo']
        fieldName = entry['FieldName']
        beginTime= entry['BeginTime']
        endtime=entry["EndTime"]
        price = entry["FinalPrice"]
        checkdata.append({
            "FieldNo":fildNo,
                "FieldTypeNo":fieldTypeNo,
                "FieldName":fieldName,
                "BeginTime":beginTime,
                "Endtime":endtime,
                "Price":price
        })
    return json.dumps(checkdata, ensure_ascii=False)


def ready_buy(tup,days_available_data, cookies, _proxies=None):
    # tup [{entry1} {entry2}]
    # dateadd 这里需要保证唯一，，，



    dateadd = int(tup[0][0])
    day_available_list = days_available_data[dateadd]  # pd

    specific_fields = []

    for _dateadd, begin_time, field_no in tup:
        # dateadd锁定某一天
        # 通过场地no和begin_time锁定买唯一entry
        df = day_available_list
        specific_fields += [df[(df['BeginTime'] == begin_time) & (df['FieldNo'] == field_no)]]

        # assert len(day_available_list) > 0
        # checkData = get_checkdata(day_available_list.iloc[0])

    if len(specific_fields):
        checkData = get_checkdata(specific_fields)
        buy_request_url = f"http://tycgs.nankai.edu.cn/Field/OrderField?checkdata={checkData}&dateadd={dateadd}&VenueNo=003"

        try:
            print(f'get: {buy_request_url}')
            rs = requests.get(buy_request_url,cookies=cookies, headers=get_hearder(),proxies=_proxies)
            return rs

        except Exception as e:
            print(f'ready_buy Error:{e}')


    else:
        print(f'未选中合理场地')


def go_buy(tup, days_data, cookies, _proxies=None):

    qcode_id = None
    try:
        rs = ready_buy(tup,days_data,cookies,_proxies).json()

        if rs['type'] == 1:
            print('Go Buy')
            qcode_id = rs['resultdata']

        else:
            print(f'some error: {rs["message"]}')

    except Exception as e:
        print(f'go_buy: {e}')


    if qcode_id:
        # paying页面 : http://tycgs.nankai.edu.cn/Views/Pay/PayField.html?OID=9c0034e5-d52f-4bad-b467-34ad6241d190&VenueNo=003
        pay_url = f'http://tycgs.nankai.edu.cn/Views/Pay/PayField.html?OID={qcode_id}&VenueNo=003'
        return pay_url



def get_test_data():
    str = '{"IsCardPay":null,"MemberNo":null,"Discount":null,"ConType":null,"type":1,"errorcode":0,"message":"获取成功","resultdata":"[{\\"BeginTime\\":\\"12:00\\",\\"EndTime\\":\\"13:30\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ001\\",\\"FieldName\\":\\"羽01\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"5.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"150\\",\\"DateBeginTime\\":\\"2024-05-13 12:00:00\\",\\"DateEndTime\\":\\"2024-05-13 13:30:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"12:00\\",\\"EndTime\\":\\"13:30\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ002\\",\\"FieldName\\":\\"羽02\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"5.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"150\\",\\"DateBeginTime\\":\\"2024-05-13 12:00:00\\",\\"DateEndTime\\":\\"2024-05-13 13:30:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"12:00\\",\\"EndTime\\":\\"13:30\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ003\\",\\"FieldName\\":\\"羽03\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"5.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"150\\",\\"DateBeginTime\\":\\"2024-05-13 12:00:00\\",\\"DateEndTime\\":\\"2024-05-13 13:30:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"12:00\\",\\"EndTime\\":\\"13:30\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ004\\",\\"FieldName\\":\\"羽04\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"5.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"150\\",\\"DateBeginTime\\":\\"2024-05-13 12:00:00\\",\\"DateEndTime\\":\\"2024-05-13 13:30:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"12:00\\",\\"EndTime\\":\\"13:30\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ005\\",\\"FieldName\\":\\"羽05\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"5.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"150\\",\\"DateBeginTime\\":\\"2024-05-13 12:00:00\\",\\"DateEndTime\\":\\"2024-05-13 13:30:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"12:00\\",\\"EndTime\\":\\"13:30\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ006\\",\\"FieldName\\":\\"羽06\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"5.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"150\\",\\"DateBeginTime\\":\\"2024-05-13 12:00:00\\",\\"DateEndTime\\":\\"2024-05-13 13:30:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"12:00\\",\\"EndTime\\":\\"13:30\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ007\\",\\"FieldName\\":\\"羽07\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"5.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"150\\",\\"DateBeginTime\\":\\"2024-05-13 12:00:00\\",\\"DateEndTime\\":\\"2024-05-13 13:30:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"12:00\\",\\"EndTime\\":\\"13:30\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ008\\",\\"FieldName\\":\\"羽08\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"5.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"150\\",\\"DateBeginTime\\":\\"2024-05-13 12:00:00\\",\\"DateEndTime\\":\\"2024-05-13 13:30:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"12:00\\",\\"EndTime\\":\\"13:30\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ009\\",\\"FieldName\\":\\"羽09\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"5.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"150\\",\\"DateBeginTime\\":\\"2024-05-13 12:00:00\\",\\"DateEndTime\\":\\"2024-05-13 13:30:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"12:00\\",\\"EndTime\\":\\"13:30\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ010\\",\\"FieldName\\":\\"羽10\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"5.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"150\\",\\"DateBeginTime\\":\\"2024-05-13 12:00:00\\",\\"DateEndTime\\":\\"2024-05-13 13:30:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"12:00\\",\\"EndTime\\":\\"13:30\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ011\\",\\"FieldName\\":\\"羽11\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"5.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"150\\",\\"DateBeginTime\\":\\"2024-05-13 12:00:00\\",\\"DateEndTime\\":\\"2024-05-13 13:30:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"12:00\\",\\"EndTime\\":\\"13:30\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ012\\",\\"FieldName\\":\\"羽12\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"5.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"150\\",\\"DateBeginTime\\":\\"2024-05-13 12:00:00\\",\\"DateEndTime\\":\\"2024-05-13 13:30:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"12:00\\",\\"EndTime\\":\\"13:30\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ013\\",\\"FieldName\\":\\"羽13\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"5.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"150\\",\\"DateBeginTime\\":\\"2024-05-13 12:00:00\\",\\"DateEndTime\\":\\"2024-05-13 13:30:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"12:00\\",\\"EndTime\\":\\"13:30\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ014\\",\\"FieldName\\":\\"羽14\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"5.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"150\\",\\"DateBeginTime\\":\\"2024-05-13 12:00:00\\",\\"DateEndTime\\":\\"2024-05-13 13:30:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"13:30\\",\\"EndTime\\":\\"14:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ001\\",\\"FieldName\\":\\"羽01\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"50\\",\\"DateBeginTime\\":\\"2024-05-13 13:30:00\\",\\"DateEndTime\\":\\"2024-05-13 14:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"13:30\\",\\"EndTime\\":\\"14:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ002\\",\\"FieldName\\":\\"羽02\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"50\\",\\"DateBeginTime\\":\\"2024-05-13 13:30:00\\",\\"DateEndTime\\":\\"2024-05-13 14:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"13:30\\",\\"EndTime\\":\\"14:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ003\\",\\"FieldName\\":\\"羽03\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"50\\",\\"DateBeginTime\\":\\"2024-05-13 13:30:00\\",\\"DateEndTime\\":\\"2024-05-13 14:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"13:30\\",\\"EndTime\\":\\"14:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ004\\",\\"FieldName\\":\\"羽04\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"50\\",\\"DateBeginTime\\":\\"2024-05-13 13:30:00\\",\\"DateEndTime\\":\\"2024-05-13 14:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"13:30\\",\\"EndTime\\":\\"14:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ005\\",\\"FieldName\\":\\"羽05\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"50\\",\\"DateBeginTime\\":\\"2024-05-13 13:30:00\\",\\"DateEndTime\\":\\"2024-05-13 14:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"13:30\\",\\"EndTime\\":\\"14:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ006\\",\\"FieldName\\":\\"羽06\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"50\\",\\"DateBeginTime\\":\\"2024-05-13 13:30:00\\",\\"DateEndTime\\":\\"2024-05-13 14:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"13:30\\",\\"EndTime\\":\\"14:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ007\\",\\"FieldName\\":\\"羽07\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"50\\",\\"DateBeginTime\\":\\"2024-05-13 13:30:00\\",\\"DateEndTime\\":\\"2024-05-13 14:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"13:30\\",\\"EndTime\\":\\"14:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ008\\",\\"FieldName\\":\\"羽08\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"50\\",\\"DateBeginTime\\":\\"2024-05-13 13:30:00\\",\\"DateEndTime\\":\\"2024-05-13 14:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"13:30\\",\\"EndTime\\":\\"14:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ009\\",\\"FieldName\\":\\"羽09\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"50\\",\\"DateBeginTime\\":\\"2024-05-13 13:30:00\\",\\"DateEndTime\\":\\"2024-05-13 14:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"13:30\\",\\"EndTime\\":\\"14:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ010\\",\\"FieldName\\":\\"羽10\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"50\\",\\"DateBeginTime\\":\\"2024-05-13 13:30:00\\",\\"DateEndTime\\":\\"2024-05-13 14:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"13:30\\",\\"EndTime\\":\\"14:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ011\\",\\"FieldName\\":\\"羽11\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"50\\",\\"DateBeginTime\\":\\"2024-05-13 13:30:00\\",\\"DateEndTime\\":\\"2024-05-13 14:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"13:30\\",\\"EndTime\\":\\"14:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ012\\",\\"FieldName\\":\\"羽12\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"50\\",\\"DateBeginTime\\":\\"2024-05-13 13:30:00\\",\\"DateEndTime\\":\\"2024-05-13 14:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"13:30\\",\\"EndTime\\":\\"14:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ013\\",\\"FieldName\\":\\"羽13\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"50\\",\\"DateBeginTime\\":\\"2024-05-13 13:30:00\\",\\"DateEndTime\\":\\"2024-05-13 14:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"13:30\\",\\"EndTime\\":\\"14:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ014\\",\\"FieldName\\":\\"羽14\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"50\\",\\"DateBeginTime\\":\\"2024-05-13 13:30:00\\",\\"DateEndTime\\":\\"2024-05-13 14:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"14:00\\",\\"EndTime\\":\\"15:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ001\\",\\"FieldName\\":\\"羽01\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 14:00:00\\",\\"DateEndTime\\":\\"2024-05-13 15:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"14:00\\",\\"EndTime\\":\\"15:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ002\\",\\"FieldName\\":\\"羽02\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 14:00:00\\",\\"DateEndTime\\":\\"2024-05-13 15:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"14:00\\",\\"EndTime\\":\\"15:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ003\\",\\"FieldName\\":\\"羽03\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 14:00:00\\",\\"DateEndTime\\":\\"2024-05-13 15:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"14:00\\",\\"EndTime\\":\\"15:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ004\\",\\"FieldName\\":\\"羽04\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 14:00:00\\",\\"DateEndTime\\":\\"2024-05-13 15:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"14:00\\",\\"EndTime\\":\\"15:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ005\\",\\"FieldName\\":\\"羽05\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 14:00:00\\",\\"DateEndTime\\":\\"2024-05-13 15:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"14:00\\",\\"EndTime\\":\\"15:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ006\\",\\"FieldName\\":\\"羽06\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 14:00:00\\",\\"DateEndTime\\":\\"2024-05-13 15:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"14:00\\",\\"EndTime\\":\\"15:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ007\\",\\"FieldName\\":\\"羽07\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 14:00:00\\",\\"DateEndTime\\":\\"2024-05-13 15:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"14:00\\",\\"EndTime\\":\\"15:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ008\\",\\"FieldName\\":\\"羽08\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 14:00:00\\",\\"DateEndTime\\":\\"2024-05-13 15:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"14:00\\",\\"EndTime\\":\\"15:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ009\\",\\"FieldName\\":\\"羽09\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 14:00:00\\",\\"DateEndTime\\":\\"2024-05-13 15:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"14:00\\",\\"EndTime\\":\\"15:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ010\\",\\"FieldName\\":\\"羽10\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 14:00:00\\",\\"DateEndTime\\":\\"2024-05-13 15:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"14:00\\",\\"EndTime\\":\\"15:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ011\\",\\"FieldName\\":\\"羽11\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 14:00:00\\",\\"DateEndTime\\":\\"2024-05-13 15:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"14:00\\",\\"EndTime\\":\\"15:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ012\\",\\"FieldName\\":\\"羽12\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 14:00:00\\",\\"DateEndTime\\":\\"2024-05-13 15:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"14:00\\",\\"EndTime\\":\\"15:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ013\\",\\"FieldName\\":\\"羽13\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 14:00:00\\",\\"DateEndTime\\":\\"2024-05-13 15:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"14:00\\",\\"EndTime\\":\\"15:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ014\\",\\"FieldName\\":\\"羽14\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 14:00:00\\",\\"DateEndTime\\":\\"2024-05-13 15:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"15:00\\",\\"EndTime\\":\\"16:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ001\\",\\"FieldName\\":\\"羽01\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 15:00:00\\",\\"DateEndTime\\":\\"2024-05-13 16:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"15:00\\",\\"EndTime\\":\\"16:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ002\\",\\"FieldName\\":\\"羽02\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 15:00:00\\",\\"DateEndTime\\":\\"2024-05-13 16:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"15:00\\",\\"EndTime\\":\\"16:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ003\\",\\"FieldName\\":\\"羽03\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 15:00:00\\",\\"DateEndTime\\":\\"2024-05-13 16:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"15:00\\",\\"EndTime\\":\\"16:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ004\\",\\"FieldName\\":\\"羽04\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 15:00:00\\",\\"DateEndTime\\":\\"2024-05-13 16:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"15:00\\",\\"EndTime\\":\\"16:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ005\\",\\"FieldName\\":\\"羽05\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 15:00:00\\",\\"DateEndTime\\":\\"2024-05-13 16:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"15:00\\",\\"EndTime\\":\\"16:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ006\\",\\"FieldName\\":\\"羽06\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 15:00:00\\",\\"DateEndTime\\":\\"2024-05-13 16:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"15:00\\",\\"EndTime\\":\\"16:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ007\\",\\"FieldName\\":\\"羽07\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 15:00:00\\",\\"DateEndTime\\":\\"2024-05-13 16:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"15:00\\",\\"EndTime\\":\\"16:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ008\\",\\"FieldName\\":\\"羽08\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 15:00:00\\",\\"DateEndTime\\":\\"2024-05-13 16:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"15:00\\",\\"EndTime\\":\\"16:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ009\\",\\"FieldName\\":\\"羽09\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 15:00:00\\",\\"DateEndTime\\":\\"2024-05-13 16:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"15:00\\",\\"EndTime\\":\\"16:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ010\\",\\"FieldName\\":\\"羽10\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 15:00:00\\",\\"DateEndTime\\":\\"2024-05-13 16:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"15:00\\",\\"EndTime\\":\\"16:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ011\\",\\"FieldName\\":\\"羽11\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 15:00:00\\",\\"DateEndTime\\":\\"2024-05-13 16:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"15:00\\",\\"EndTime\\":\\"16:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ012\\",\\"FieldName\\":\\"羽12\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 15:00:00\\",\\"DateEndTime\\":\\"2024-05-13 16:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"15:00\\",\\"EndTime\\":\\"16:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ013\\",\\"FieldName\\":\\"羽13\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 15:00:00\\",\\"DateEndTime\\":\\"2024-05-13 16:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"15:00\\",\\"EndTime\\":\\"16:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ014\\",\\"FieldName\\":\\"羽14\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"10.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 15:00:00\\",\\"DateEndTime\\":\\"2024-05-13 16:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"16:00\\",\\"EndTime\\":\\"17:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ001\\",\\"FieldName\\":\\"羽01\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 16:00:00\\",\\"DateEndTime\\":\\"2024-05-13 17:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"16:00\\",\\"EndTime\\":\\"17:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ002\\",\\"FieldName\\":\\"羽02\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 16:00:00\\",\\"DateEndTime\\":\\"2024-05-13 17:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"16:00\\",\\"EndTime\\":\\"17:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ003\\",\\"FieldName\\":\\"羽03\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 16:00:00\\",\\"DateEndTime\\":\\"2024-05-13 17:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"16:00\\",\\"EndTime\\":\\"17:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ004\\",\\"FieldName\\":\\"羽04\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 16:00:00\\",\\"DateEndTime\\":\\"2024-05-13 17:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"16:00\\",\\"EndTime\\":\\"17:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ005\\",\\"FieldName\\":\\"羽05\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 16:00:00\\",\\"DateEndTime\\":\\"2024-05-13 17:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"16:00\\",\\"EndTime\\":\\"17:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ006\\",\\"FieldName\\":\\"羽06\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 16:00:00\\",\\"DateEndTime\\":\\"2024-05-13 17:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"16:00\\",\\"EndTime\\":\\"17:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ007\\",\\"FieldName\\":\\"羽07\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 16:00:00\\",\\"DateEndTime\\":\\"2024-05-13 17:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"16:00\\",\\"EndTime\\":\\"17:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ008\\",\\"FieldName\\":\\"羽08\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 16:00:00\\",\\"DateEndTime\\":\\"2024-05-13 17:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"16:00\\",\\"EndTime\\":\\"17:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ009\\",\\"FieldName\\":\\"羽09\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 16:00:00\\",\\"DateEndTime\\":\\"2024-05-13 17:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"16:00\\",\\"EndTime\\":\\"17:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ010\\",\\"FieldName\\":\\"羽10\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 16:00:00\\",\\"DateEndTime\\":\\"2024-05-13 17:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"16:00\\",\\"EndTime\\":\\"17:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ011\\",\\"FieldName\\":\\"羽11\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 16:00:00\\",\\"DateEndTime\\":\\"2024-05-13 17:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"16:00\\",\\"EndTime\\":\\"17:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ012\\",\\"FieldName\\":\\"羽12\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 16:00:00\\",\\"DateEndTime\\":\\"2024-05-13 17:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"16:00\\",\\"EndTime\\":\\"17:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ013\\",\\"FieldName\\":\\"羽13\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 16:00:00\\",\\"DateEndTime\\":\\"2024-05-13 17:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"16:00\\",\\"EndTime\\":\\"17:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ014\\",\\"FieldName\\":\\"羽14\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 16:00:00\\",\\"DateEndTime\\":\\"2024-05-13 17:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"17:00\\",\\"EndTime\\":\\"18:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ001\\",\\"FieldName\\":\\"羽01\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 17:00:00\\",\\"DateEndTime\\":\\"2024-05-13 18:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"17:00\\",\\"EndTime\\":\\"18:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ002\\",\\"FieldName\\":\\"羽02\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 17:00:00\\",\\"DateEndTime\\":\\"2024-05-13 18:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"17:00\\",\\"EndTime\\":\\"18:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ003\\",\\"FieldName\\":\\"羽03\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 17:00:00\\",\\"DateEndTime\\":\\"2024-05-13 18:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"17:00\\",\\"EndTime\\":\\"18:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ004\\",\\"FieldName\\":\\"羽04\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 17:00:00\\",\\"DateEndTime\\":\\"2024-05-13 18:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"17:00\\",\\"EndTime\\":\\"18:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ005\\",\\"FieldName\\":\\"羽05\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 17:00:00\\",\\"DateEndTime\\":\\"2024-05-13 18:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"17:00\\",\\"EndTime\\":\\"18:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ006\\",\\"FieldName\\":\\"羽06\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 17:00:00\\",\\"DateEndTime\\":\\"2024-05-13 18:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"17:00\\",\\"EndTime\\":\\"18:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ007\\",\\"FieldName\\":\\"羽07\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 17:00:00\\",\\"DateEndTime\\":\\"2024-05-13 18:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"17:00\\",\\"EndTime\\":\\"18:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ008\\",\\"FieldName\\":\\"羽08\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 17:00:00\\",\\"DateEndTime\\":\\"2024-05-13 18:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"17:00\\",\\"EndTime\\":\\"18:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ009\\",\\"FieldName\\":\\"羽09\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 17:00:00\\",\\"DateEndTime\\":\\"2024-05-13 18:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"17:00\\",\\"EndTime\\":\\"18:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ010\\",\\"FieldName\\":\\"羽10\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 17:00:00\\",\\"DateEndTime\\":\\"2024-05-13 18:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"17:00\\",\\"EndTime\\":\\"18:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ011\\",\\"FieldName\\":\\"羽11\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 17:00:00\\",\\"DateEndTime\\":\\"2024-05-13 18:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"17:00\\",\\"EndTime\\":\\"18:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ012\\",\\"FieldName\\":\\"羽12\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 17:00:00\\",\\"DateEndTime\\":\\"2024-05-13 18:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"17:00\\",\\"EndTime\\":\\"18:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ013\\",\\"FieldName\\":\\"羽13\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 17:00:00\\",\\"DateEndTime\\":\\"2024-05-13 18:00:00\\",\\"TimePeriod\\":\\"1\\"},{\\"BeginTime\\":\\"17:00\\",\\"EndTime\\":\\"18:00\\",\\"Count\\":\\"14\\",\\"FieldNo\\":\\"JNYMQ014\\",\\"FieldName\\":\\"羽14\\",\\"FieldTypeNo\\":\\"JNYMQ\\",\\"FinalPrice\\":\\"0.00\\",\\"TimeStatus\\":\\"0\\",\\"FieldState\\":\\"1\\",\\"IsHalfHour\\":\\"1\\",\\"ShowWidth\\":\\"100\\",\\"DateBeginTime\\":\\"2024-05-13 17:00:00\\",\\"DateEndTime\\":\\"2024-05-13 18:00:00\\",\\"TimePeriod\\":\\"1\\"}]"}'

    return {0:json.loads(json.loads(str)['resultdata'])}

def get_remote_data(cookie,Test=False):

    days_data = get_all_pds(cookie, days=[0, 1, 2, 3], Test=Test)

    return get_all_available(days_data)