import pickle, json, time
import pandas as pd
from utils.api import get_venue_raw_data, get_checkdata,get_hearder
from api.sso2 import get_sso_jwt
from utils.cookie_control import load_cookies, are_cookies_valid
import requests

from datetime import timedelta

class NkuVenue:
    
    def __init__(self, username, password, logger):
        self.days = 4
        self.periods = 3 
        self.per_day_num = 14 * 14
        self.venue_num = 14
        self.username = username
        self.password = password
        
        self.init_venue_pd()

        self.logger = logger

        # proxies = {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080", }
        # self.proxies = proxies
        self.proxies =None
        self.cookie = {}
        self.update_cookie()

    def cookies_is_mine(self, cdt):
        if cdt and 'username' in cdt:
            return cdt['username']['value'] == self.username
        return False

    def _update_cookie(self):
        self.logger.info("[SYS] 模拟登录...")
        cdt = get_sso_jwt(self.username, self.password)

        self.cookie['JWTUserToken'] = cdt['JWTUserToken']
        self.cookie['UserId'] = cdt['UserId']
        self.cookie['ASP.NET_SessionId'] = cdt['ASP.NET_SessionId']
        
    def update_cookie(self):
        """{
                'LoginType': '1',
                'ASP.NET_SessionId': 'z52ivhknf1oaxipfnmdkgtbp',
                'JWTUserToken': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJuYW1lIjoiOTQ4MDg5NTMtNTIwOS00OTVkLWFhZmMtZjhlNTVlY2I4Zjk0IiwiZXhwIjoxNzI2NDE1OTk2LjAsImp0aSI6ImxnIiwiaWF0IjoiMjAyNC0wOS0wOSAwMzo1OTo1NiJ9.gigipOzCECrWA6BJGfHIxax3-SJF5JF0P2pTi0XZAaA',
                'UserId': '94808953-5209-495d-aafc-f8e55ecb8f94',
                'LoginSource': '1',}
        """
        self.logger.info('尝试读取jwt令牌')
        self.cookie = {'LoginType': '1',  'LoginSource': '1',}

        cdt = load_cookies()
        if cdt and are_cookies_valid(cdt) and self.cookies_is_mine(cdt):
                
            self.cookie['JWTUserToken'] = cdt['JWTUserToken']['value']
            self.cookie['UserId'] = cdt['UserId']['value']
            self.cookie['ASP.NET_SessionId'] = cdt['ASP.NET_SessionId']['value']
        else:
            self.logger.info('尝试读取jwt令牌 错误')
            self._update_cookie()
    
    def init_venue_pd(self):
        # df = pd.DataFrame([],columns=['BeginTime', 'EndTime', 'Count', 'FieldNo', 'FieldName', 'FieldTypeNo',
        #     'FinalPrice', 'TimeStatus', 'FieldState', 'IsHalfHour', 'ShowWidth',
        #     'DateBeginTime', 'DateEndTime', 'TimePeriod'],index=[0])

        # self.raw_json_list = pickle.load(open('test_tmp_data/test_raw_list.list','rb'))
        # self.venue_pd = pickle.load(open('test_tmp_data/test_Data.pd','rb'))
        self.raw_json_list = None
        self.venue_pd = None

    def refrash_venue_pd(self):
        self.logger.info('刷新场地信息')
        if not self.raw_json_list :
            try:
                self.raw_json_list = get_venue_raw_data(self.cookie, list(range(self.days)))
                self.venue_pd = pd.DataFrame(self.raw_json_list)
                
            except json.JSONDecodeError as e:
                self._update_cookie()
                self.raw_json_list = get_venue_raw_data(self.cookie, list(range(self.days)))
                self.venue_pd = pd.DataFrame(self.raw_json_list)
            except Exception as e:
                pass

            # 确保 DateBeginTime 列是 datetime 类型
            self.venue_pd['DateBeginTime'] = pd.to_datetime(self.venue_pd['DateBeginTime'])

            # 根据索引调整 DateBeginTime 列
            self.venue_pd['DateBeginTime'] = self.venue_pd.apply(
                lambda row: row['DateBeginTime'] + timedelta(days=0) if row.name < self.per_day_num
                else row['DateBeginTime'] + timedelta(days=1) if row.name < self.per_day_num * 2
                else row['DateBeginTime'] + timedelta(days=2) if row.name < self.per_day_num * 3
                else row['DateBeginTime'] + timedelta(days=3) , axis=1
            )
            # 2. date
            self.venue_pd['Date'] = self.venue_pd['DateBeginTime'].dt.date

            # 3. 新增一列表示星期几
            self.venue_pd['WeekDay'] = self.venue_pd['DateBeginTime'].dt.day_name()

            # 4. 提取时间（时分）
            self.venue_pd['TimeOnly'] = self.venue_pd['DateBeginTime'].dt.strftime('%H:%M')
    
    def _filter(self,*key, **param):
        return filter(self.venue_pd,*key, **param)



    def rub(self, checkData, dateadd, logger):
        """
            直接提交订阅数据checkData，不经过服务器传来最新的raw_data，但依旧需要cookie， 
            注意: checkData无法保证场地的有效性
            return bool, mess = {'message':'', 'resultdata':xxx}
        """
        buy_request_url = f"http://tycgs.nankai.edu.cn/Field/OrderField?checkdata={checkData}&dateadd={dateadd}&VenueNo=003"
        pay_field_url = "http://tycgs.nankai.edu.cn/Views/Pay/PayField.html?OID={}&VenueNo=003"
        try:
            #print(f'Request to buy, order status:{checkData}')
            rs = requests.get(buy_request_url,cookies=self.cookie, headers=get_hearder(),proxies=self.proxies)

            try:
                mess = rs.json()
                if mess['resultdata']:
                    logger.info(f'[SUCCESS],resultdata: {mess["resultdata"]}')
                    mess['paying_link'] = pay_field_url.format(mess['resultdata'])
                    return True, mess
                else:
                    logger.info(f"order is not valid, the reason: {mess['message']}")
                    return False, mess

            except json.JSONDecodeError:
                # 这个错误大概率是令牌过期了 
                logger.info('response is not a json，查看post格式以及是否登录，正在尝试重新登录...')
                self._update_cookie()
                rs = requests.get(buy_request_url, cookies=self.cookie, headers=get_hearder(), proxies=self.proxies)
                mess = rs.json()
                if mess['resultdata']:
                    logger.info(f'[SUCCESS],resultdata: {mess["resultdata"]}')
                    mess['paying_link'] = pay_field_url.format(mess['resultdata'])
                    return True, mess
                else:
                    logger.info(f"order is not valid, the reason: {mess['message']}")
                    return False,mess

        except Exception as e:
            logger.info(f'[DEAFEAT] Request to buy, but Error:{e}')
            return False,mess
        
    """
        这里是和微信进行交互的
    """
    def filter_by_day(self, df, start_time, end_time, day_of_week=None):

        df['TimeOnly'] = pd.to_datetime(df['DateBeginTime'].dt.strftime('%H:%M'), format='%H:%M').dt.time
        # 筛选空闲
        filtered_df = df[(df['TimeStatus'] == '1') & (df['FieldState'] == '0')]
        
        # 筛选星期几
        if day_of_week and isinstance(day_of_week, list):
            filtered_df = filtered_df[filtered_df['WeekDay'].isin(day_of_week)]
        
        # 筛选时间段
        tp = pd.DataFrame()
        for st, ed in zip(start_time, end_time):
            st_time = pd.to_datetime(st, format='%H:%M').time()
            ed_time = pd.to_datetime(ed, format='%H:%M').time()
            tp = pd.concat([tp, filtered_df[(filtered_df['TimeOnly'] >= st_time) & (filtered_df['TimeOnly'] <= ed_time)]], axis=0)
        
        return tp 


    def send_report_to_wechat(self, report_data, corpid='ww689c8f801cca2275', secret='O-QnkbszBmAwhq5Ju6aWfJwGY9YyqJrXs-69MgqWT3k', agent_id=1000003, users=None):
        try:
            users = ["Lijiahao"]
            user_str = '|'.join(users)

            #step1 get access-token
            r = requests.get(f'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corpid}&corpsecret={secret}')
            access_token = r.json()['access_token']

            #step2
            mess = {
                "touser" : user_str,
                "msgtype" : "text",
                "agentid" : agent_id,
                "text" : { "content" : report_data},
                "safe":0
            }

            r = requests.post(f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}', json=mess)
            self.logger.info(f'发送给微信:{report_data}, 得到回复:{(r.content)}')
            
        except Exception as e:
            print(e)
            
    def report_free_venues(self):
        previous_state = {}  # 存储之前的场地状态
        start_time = ['8:00','18:00', '19:00', '20:00', '21:00']
        end_time = ['9:00','19:00', '20:00', '21:00', '22:00']


        while True:
            self.refrash_venue_pd()
            free_venues = self.filter_by_day(self.venue_pd, start_time, end_time)

            # 汇报变化
            report_data = {}
            # 冷启动
            if not previous_state.__len__():
                for index, row in free_venues.iterrows():
                    venue_no = row['FieldNo']
                    time_slot = row['WeekDay'] + "-" + str(row['TimeOnly'])
                    if time_slot not in report_data:
                        report_data[time_slot] = []
                    report_data[time_slot].append(venue_no[-2:])
                    previous_state[time_slot + venue_no] = 'free'
            else:
                for index, row in free_venues.iterrows():
                    venue_no = row['FieldNo']
                    time_slot = row['WeekDay'] + "-" + str(row['TimeOnly'])

                    # 检查场地之前的状态是否为空闲
                    if venue_no in previous_state and previous_state[time_slot + venue_no] == 'occupied':
                        if time_slot not in report_data:
                            report_data[time_slot] = []
                        report_data[time_slot].append(venue_no[-2:])
                    previous_state[time_slot + venue_no] = 'free'

            self.logger.info(f'report_data size: {report_data.__len__()}')
            
            # 汇报给微信服务器
            if report_data:
                self.logger.info(f'当前空闲场地信息{report_data}')
                current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                content = f"空场提示-"+ current_time + json.dumps(report_data, ensure_ascii=False)
                self.send_report_to_wechat(content)

            time.sleep(60*10)
def filter(df, *key, **param):

    filtered_pd = df
    if 'index_start' in param or 'index_end' in param:
        index_start = param.get('index_start', filtered_pd.index.min())
        index_end = param.get('index_end', filtered_pd.index.max())
        filtered_pd = filtered_pd.loc[index_start:index_end]
        
    # 使用传入的key和param筛选
    for k, v in param.items():
        if k in filtered_pd.columns:
            filtered_pd = filtered_pd[filtered_pd[k] == v]
            
    return filtered_pd


if __name__ == '__main__':
    from utils.logger import logger

    username='2111252'
    password='123'
    agent = NkuVenue(username, password,logger)
    # agent.update_cookie()
    # agent.refrash_venue_pd()
    # ret, mess = agent.order_by_time([0,1,2,3], ['8','9'], timeout=20, refrash_interval=5,succession=True)
    atime = [8, 9]
    price = 0
    checkData2 = (f'[{{"FieldNo": "JNYMQ0{str(7).zfill(2)}", "FieldTypeNo": "JNYMQ", "FieldName": "羽{str(7).zfill(2)}", "BeginTime": "{12}:00", "Endtime": "{13}:30", "Price": "{price}.00"}}]')
    agent.rub(checkData=checkData2, dateadd=3, logger=logger)
    #print(ret, mess)


