import pickle, json, time
import pandas as pd
from utils.api import get_venue_raw_data, get_checkdata,get_hearder
from api.sso import get_sso_jwt
from utils.cookie_control import load_cookies, are_cookies_valid
import requests
from datetime import datetime


class NkuVenue:
    
    def __init__(self, username, password):
        self.days = 4
        self.periods = 3 
        self.per_day_num = 14 * 14
        self.venue_num = 14
        self.username = username
        self.password = password
        
        self.init_venue_pd()
        
        self.proxies = None
        self.cookie = {}
        
    def _update_cookie(self):
            cdt =  get_sso_jwt(self.username, self.password)
        
            self.cookie['JWTUserToken'] = cdt['JWTUserToken']
            self.cookie['UserId'] = cdt['UserId']
            self.cookie['ASP.NET_SessionId'] = cdt['ASP.NET_SessionId']    

    def cookies_is_mine(self, cdt):
        if cdt and 'username' in cdt:
            return cdt['username']['value'] == self.username
        return False
    def update_cookie(self):
        """{
                'LoginType': '1',
                'ASP.NET_SessionId': 'z52ivhknf1oaxipfnmdkgtbp',
                'JWTUserToken': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJuYW1lIjoiOTQ4MDg5NTMtNTIwOS00OTVkLWFhZmMtZjhlNTVlY2I4Zjk0IiwiZXhwIjoxNzI2NDE1OTk2LjAsImp0aSI6ImxnIiwiaWF0IjoiMjAyNC0wOS0wOSAwMzo1OTo1NiJ9.gigipOzCECrWA6BJGfHIxax3-SJF5JF0P2pTi0XZAaA',
                'UserId': '94808953-5209-495d-aafc-f8e55ecb8f94',
                'LoginSource': '1',}
        """
        print('获取jwt令牌')
        self.cookie = {'LoginType': '1',  'LoginSource': '1',}
        
        cdt = load_cookies()
        if cdt and are_cookies_valid(cdt) and self.cookies_is_mine(cdt):
                
            self.cookie['JWTUserToken'] = cdt['JWTUserToken']['value']
            self.cookie['UserId'] = cdt['UserId']['value']
            self.cookie['ASP.NET_SessionId'] = cdt['ASP.NET_SessionId']['value']
        else: 
            self._update_cookie()
    
    def init_venue_pd(self):
        # df = pd.DataFrame([],columns=['BeginTime', 'EndTime', 'Count', 'FieldNo', 'FieldName', 'FieldTypeNo',
        #     'FinalPrice', 'TimeStatus', 'FieldState', 'IsHalfHour', 'ShowWidth',
        #     'DateBeginTime', 'DateEndTime', 'TimePeriod'],index=[0])
        self.raw_json_list = None
        self.venue_pd = None
        #self.raw_json_list = pickle.load(open('test_tmp_data/test_raw_list.list','rb'))
        #self.venue_pd = pickle.load(open('test_tmp_data/test_Data.pd','rb'))


    def refrash_venue_pd(self):
        print('刷新场地信息')
        if not self.raw_json_list :
            try:
                self.raw_json_list = get_venue_raw_data(self.cookie, list(range(self.days)))
                self.venue_pd = pd.DataFrame(self.raw_json_list)
                
            except json.JSONDecodeError as e:
                self.update_cookie()
                self.raw_json_list = get_venue_raw_data(self.cookie, list(range(self.days)))
                self.venue_pd = pd.DataFrame(self.raw_json_list)
            except Exception as e:
                pass
                
            
    def _filter(self,*key, **param):
        return filter(self.venue_pd,*key, **param)


    def _query_by_day(self, day: int, begin_time: list):
        # day: 0-3 今天 明天 后天 大后天
        # bigin_time[str, ]: [18:00, 19:00]  
        # return [index0, index1]
        # return [index] 
        
        free_venues = self._filter(TimeStatus='1', FieldState='0',
                                   index_start=day*self.per_day_num, 
                                   index_end=(day+ 1)*self.per_day_num)
        ret = None
        
        begin_time0 = begin_time[0] 
        a1 = filter(free_venues, BeginTime=begin_time0)
        #print(a1)
        res = {i:None for i in range(1,15)}
        for i in a1.index:
            res[int(a1.loc[i]['FieldName'][1:])] = i
        
            
        if begin_time.__len__() == 1:
            for no, id in res.items():
                if id: 
                    ret = [id]
                    break
        else:
            a2 = filter(free_venues, BeginTime=begin_time[1])
            res_ = {i:None for i in range(1,15)}
            for i in a2.index:
                res_[int(a2.loc[i]['FieldName'][1:])] = i
            
            # 1个场地连续2场
            for no, id in res.items():
                if id and res_[no]:
                    ret = [id, res_[no]]
                    break
                
            # 2个场地 2场
            if not ret:
                ret = []
                for venue_no, indx in res.items():
                    if indx:
                        ret.append(indx)
                        break
                for venue_no, indx in res_.items():
                    if indx:
                        ret.append(indx)
                        break                
                
        return ret

    def query_by_day(self, day: int, begin_times, succession=False):
        # day int: 0-4
        # begin_time: str or [str, str]: 8 - 21
        # succseeion  确保有两个场地
        # return [series] 
        if not isinstance(begin_times, list):
            begin_times = [begin_times]
            
        begin_times = [begin_time + ':00' for begin_time in begin_times]
        res = self._query_by_day(day,begin_time=begin_times) 
        #print(res)            
        
        # succession
        if succession and res.__len__() < 2:
            return None    
           
        if res:
            res = [self.venue_pd.loc[i] for i in res]
        
        return res
    
    def _order(self, dateadd, order_panda):
        
        checkData = get_checkdata(order_panda)
        buy_request_url = f"http://tycgs.nankai.edu.cn/Field/OrderField?checkdata={checkData}&dateadd={dateadd-1}&VenueNo=003"
        try:
            print(f'Request to buy, order status:{checkData}')
            rs = requests.get(buy_request_url,cookies=self.cookie, headers=get_hearder(),proxies=self.proxies)
            return rs

        except Exception as e:
            print(f'Request to buy, but Error:{e}')
            return 'error'

    def order_by_time(self, days_range:list, begin_times:list, timeout=60, refrash_interval=2, succession=False):
        """
        循环查询指定时间段的场地，直到找到可用场地，然后发送预定请求
        
        days_range: [0,1,2,3]
        begin_times: ['8','9']
        Returns:
                ret:bool, mess = {'message':'success',
                            'resultdata':xxx}
        """
        st_time = time.time()
        flag = True
        mess = None
        ret = False
        while flag:
            self.refrash_venue_pd()
            
            for day in days_range:
                res = self.query_by_day(day, begin_times, succession=succession)
                
                if res:
                    print(f"Find available venue success:{day} {[p['FieldName']+'-'+p['BeginTime'] for p in res]}")
                    
                    res = self._order(day, res)
                    print('Request send reserve message success')
                    try:
                        mess = res.json()
                        ret = True
                        break
                    except Exception as e:
                        print('some error',{e})
                        mess = {'message':'发送订单成功，但是解析返回数据错误，目标不是json格式或者网络问题',
                            'resultdata':None}
                    finally:
                        flag = False      

            print(f'{datetime.now().strftime("%Y-%m-%d-%H:%M:%S")} 未查询{days_range} {begin_times}' )
            if time.time() - st_time > timeout:
                flag = False
                mess = {'message':'Timeout 没有空闲场地', 'resultdata':None}
                print(f'Time out, order({days_range} {begin_times}) failed')
            time.sleep(refrash_interval)
        return ret, mess
    
    def order_specific(self,venue_no:int, day:int, begin_times:int, timeout=60):
        """
            订阅特定一个场地，循环到到可以订或者timeout

        Returns:
             ret:bool, mess = {'message':'success',
                            'resultdata':xxx}
        """
        venue_no = f'JNYMQ0{str(venue_no).zfill(2)}'
        begin_times = f'{str(begin_times)}:00'
        
        st_time = time.time()
        flag = True
        mess = None
        ret = False
        while flag:
            if time.time() - st_time > timeout:
                flag = False
                mess = {'message':'Timeout 没有空闲场地',
                        'resultdata':None}
                print(f'Time out, order_specific[{venue_no} {day} {begin_times}:00] failed')
            
            free_venues = self._filter(
                                    TimeStatus='1', FieldState='0',
                                    index_start = day*self.per_day_num, 
                                    index_end = (day+ 1)*self.per_day_num,
                                    BeginTime = begin_times,
                                    FieldNo = venue_no
                                    )
                
            if free_venues.__len__() > 0:
                print(f"Find available venue({venue_no, begin_times, day}) success")
                res = self._order(day, free_venues)
 
                try:
                    mess = res.json()
                except Exception as e:
                    print('some error',{e})
                    mess = {'message':'发送订单成功，但是解析返回数据错误，目标不是json格式或者网络问题',
                        'resultdata':None}
                finally:
                    flag = False
        return ret, mess


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

    username=''
    password=''
    agent = NkuVenue(username, password)
    # agent.update_cookie()
    # agent.refrash_venue_pd()
    ret, mess = agent.order_by_time([0,1,2,3], ['8','9'], timeout=20, refrash_interval=5,succession=True)
    print(ret, mess)