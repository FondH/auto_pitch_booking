import requests
import time, json
from utils.logger import logger
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

def get_venue_raw_data(cookie, days):
    """

    :param cookie:
    :return: {0:[{},{}], 1:[{},{}] }
    """
    # dateadd 0-3 表示今天、明天、后天、大后天（可以无）


    logger.info(f'get_all_list: refresh field data')
    _url = 'http://tycgs.nankai.edu.cn/Field/GetVenueStateNew?dateadd={}&TimePeriod={}&VenueNo=003&FieldTypeNo=JNYMQ&_={}'
    status = []
    for i in days:

        for period in range(3):
            tar_u = _url.format(i, period,get_tp())
            try:
                rs = requests.get(tar_u,headers=get_hearder(),cookies=cookie)
                rs.raise_for_status()

                json_data = dict(rs.json())
                
                if isinstance(json_data['resultdata'], str):
                    result_data = json.loads(json_data['resultdata'])
                else:
                    result_data = json_data['resultdata']

                status += result_data
                time.sleep(0.2)
            except json.JSONDecodeError as e:
                logger.warning(f"Error decoding JSON: , 应该是令牌未加载或者过期了")
                raise

            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                raise

            except Exception as e:
                logger.error("获得目标数据失败",e)



    return status

def get_checkdata(entrys):
    checkdata = []
    if not isinstance(entrys, list):
        entrys = [entrys]

    for entry in entrys:
        #entry = entry.iloc[0]
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