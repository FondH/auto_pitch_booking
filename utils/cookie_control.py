
import pickle,os
from datetime import datetime
from http.cookies import SimpleCookie

COOKIE_PATH = os.getcwd() + '/test_tmp_data/cookies.pkl'

def dump_cookies(cookie, file_path=COOKIE_PATH):
    cookies = {}
    for key, value in cookie.items():
        cookies[key] = {
            'value': value,
            'expires': 0
        }
        
    with open(COOKIE_PATH, 'wb') as file:
        pickle.dump(cookies, file)
    print(f"Cookies 已保存至{COOKIE_PATH}.")
    


        
# 从文件加载 Cookies
def load_cookies(file_path=COOKIE_PATH):
    try:
        with open(file_path, 'rb') as file:
            cookies = pickle.load(file)
            return cookies
    except FileNotFoundError:
        print("未找到 cookies 文件.")
        return None

def are_cookies_valid(cookies):
    if cookies:
        if not ('ASP.NET_SessionId' in cookies and 'JWTUserToken' in cookies and 'UserId' in cookies):
            return False
        # for cookie_info in cookies.values():
        #     if is_cookie_expired(cookie_info):
        #         return False
        return True


def is_cookie_expired(cookie_info):
    if cookie_info['expires']:
        return cookie_info['expires'] < datetime.utcnow()
    return False 




# cookies = load_cookies()
# if are_cookies_valid(cookies):
#     print("Cookies 有效, 可以使用.")
# else:
#     print("Cookies 已过期，需要重新获取.")
