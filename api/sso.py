"""
    调用 get_sso_jwt(username, password) 得到sso.nankai.edu.cn 的jwt 和 userid
    逻辑过程 /doc/sso流程.md 里面
    Returns:
        _dict_: {
                'JWTUserToken' : 
                'UserId' : 
                ...
                }
"""
import hashlib, time, re
import random, datetime, base64
import requests
from utils.cookie_control import dump_cookies

def hex_md5(s):
    md5_hash = hashlib.md5()
    md5_hash.update(s.encode('utf-8'))
    return md5_hash.hexdigest()


def parse_headers(header_string):
    headers = {}
    for line in header_string.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            headers[key.strip()] = value.strip()
    return headers


def get_sso_jwt(username='2111252', password='123456'):
    password = hex_md5(password)
    print(f"your account: \n\tusername:{username} \n\thash_pass:{password}")
    session = requests.Session()
    proxies = {
        'http': 'http://127.0.0.1:8080',
        'https': 'http://127.0.0.1:8080',
    }
    ver = True
    _lt = None
    #session.proxies.update(proxies)


    # step -1 get the login page
    _u = 'https://sso.nankai.edu.cn/sso/login?service=http://tycgs.nankai.edu.cn/User/LoginCas'
    resp = session.get(_u, timeout=10, verify=ver)
    print('\nstep -1 /sso/login?service:', resp.status_code)
    match = re.search(r"var _lt\s*=\s*\"(\d+)\";", resp.text)
    if match:
        _lt = match.group(1)
        print('\t_lt get:', _lt)
    else :
        print('\tlt not found')
        
        
    # step 0 get the loadcode(to get the value of `rand` )
    hd0 = f"""
            Host: sso.nankai.edu.cn
            Content-Length: 0
            Sec-Ch-Ua: "Chromium";v="113", "Not-A.Brand";v="24"
            Accept: application/json, text/javascript, */*; q=0.01
            X-Requested-With: XMLHttpRequest
            Sec-Ch-Ua-Mobile: ?0
            Authorization: MTE1MjcxOTA1NDIxODc3MzQwNzA4
            User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5672.127 Safari/537.36
            Sec-Ch-Ua-Platform: "Windows"
            Origin: https://sso.nankai.edu.cn
            Sec-Fetch-Site: same-origin
            Sec-Fetch-Mode: cors
            Sec-Fetch-Dest: empty
            Referer: https://sso.nankai.edu.cn/sso/login?service=http://tycgs.nankai.edu.cn/User/LoginCas
            Accept-Encoding: gzip, deflate
            Accept-Language: zh-CN,zh;q=0.9
            Connection: close
        """
    hd0 = parse_headers(hd0)
    now = datetime.datetime.now()
    year = now.year
    time_in_ms = int(now.timestamp() * 1000)  # 转换为 JavaScript 中的毫秒时间戳
    calculation_result = year * time_in_ms * 33
    random_number = random.randint(0, 999)
    string_to_encode = f"{calculation_result}{random_number}"
    hd0['Authorization'] = base64.b64encode(string_to_encode.encode()).decode()

    loadcode_url = 'https://sso.nankai.edu.cn/sso/loadcode'

    r = session.post(loadcode_url, headers=hd0, verify=ver)
    rand = r.json()['rand']
    print('\nstep 0  /sso/loadcode:', r.text, r.status_code,)


    # step 1 get the checkRole
    hd1 = f"""
    Host: sso.nankai.edu.cn
    Content-Length: 352
    Sec-Ch-Ua: "Chromium";v="113", "Not-A.Brand";v="24"
    Accept: application/json, text/javascript, */*; q=0.01
    Content-Type: application/x-www-form-urlencoded; charset=UTF-8
    X-Requested-With: XMLHttpRequest
    Sec-Ch-Ua-Mobile: ?0
    User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5672.127 Safari/537.36
    Sec-Ch-Ua-Platform: "Windows"
    Origin: https://sso.nankai.edu.cn
    Sec-Fetch-Site: same-origin
    Sec-Fetch-Mode: cors
    Sec-Fetch-Dest: empty
    Referer: https://sso.nankai.edu.cn/sso/login?service=http://tycgs.nankai.edu.cn/User/LoginCas
    Accept-Encoding: gzip, deflate
    Accept-Language: zh-CN,zh;q=0.9
    Connection: close""" 
    hd1 = parse_headers(hd1)
    t = r'Za+py8s3eSjcMLmoEj8f9UEiZoXZMqs/rR6KkShFF28iN0Zru7dOCTjHKveFRnFX4142/T7JlhOUhZgW60d5b3ZX0oHdChW8g06TOL3CH7T9X3q+Ul4drFs7OSUesPQBbi/sX09eAFDTNsbztP3upBYp7L8ch7d8jcWwBWeTekg='
    info = {
            'username':username, 
            'password':password, 
            't':f'{t}',
            'rand':f'{rand}', 
            'service':'http://tycgs.nankai.edu.cn/User/LoginCas', 
            'loginType':0
            }
    #r = requests.post('https://sso.nankai.edu.cn/sso/checkRole', headers=hd1, cookies=cookie,data=info)

    r = session.post('https://sso.nankai.edu.cn/sso/checkRole', headers=hd1,data=info, verify=ver)
    print('\nstep 1  /sso/checkRole:', r.text, r.status_code)
    time.sleep(0.5)

    # step 2 get the checkWeak
    hd2 = f"""
    Host: sso.nankai.edu.cn
    Content-Length: 58
    Sec-Ch-Ua: "Chromium";v="113", "Not-A.Brand";v="24"
    Accept: application/json, text/javascript, */*; q=0.01
    Content-Type: application/x-www-form-urlencoded; charset=UTF-8
    X-Requested-With: XMLHttpRequest
    Sec-Ch-Ua-Mobile: ?0
    User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5672.127 Safari/537.36
    Sec-Ch-Ua-Platform: "Windows"
    Origin: https://sso.nankai.edu.cn
    Sec-Fetch-Site: same-origin
    Sec-Fetch-Mode: cors
    Sec-Fetch-Dest: empty
    Referer: https://sso.nankai.edu.cn/sso/login?service=http://tycgs.nankai.edu.cn/User/LoginCas
    Accept-Encoding: gzip, deflate
    Accept-Language: zh-CN,zh;q=0.9
    Connection: close"""

    hd2 = parse_headers(hd2)
    check_role_url = 'https://sso.nankai.edu.cn/sso/checkWeak'

    # r = requests.post(check_role_url, headers=hd2, 
    #                   cookies=cookie,
    #                   data={'username':'2111252', 'password':'3eb6024b17f2dc0788c419255ed5eb3b'})
    r = session.post(
                    check_role_url, headers=hd2,
                    data={'username':username, 'password':password}, 
                    verify=ver
                    )
    print('\nstep 2  /sso/checkWeak:', r.text, r.status_code)


    # step 3 get the login
    h3 = f"""
    Host: sso.nankai.edu.cn
    Content-Length: 386
    Sec-Ch-Ua: "Chromium";v="113", "Not-A.Brand";v="24"
    Accept: application/json, text/javascript, */*; q=0.01
    Content-Type: application/x-www-form-urlencoded; charset=UTF-8
    X-Requested-With: XMLHttpRequest
    Sec-Ch-Ua-Mobile: ?0
    User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5672.127 Safari/537.36
    Sec-Ch-Ua-Platform: "Windows"
    Origin: https://sso.nankai.edu.cn
    Sec-Fetch-Site: same-origin
    Sec-Fetch-Mode: cors
    Sec-Fetch-Dest: empty
    Referer: https://sso.nankai.edu.cn/sso/login?service=http://tycgs.nankai.edu.cn/User/LoginCas
    Accept-Encoding: gzip, deflate
    Accept-Language: zh-CN,zh;q=0.9
    Connection: close
    """
    hd3 = parse_headers(h3)
    info2 = {'ajax':'1',
            'username':username, 
            'password':password, 
            'lt':f'{_lt}',
            'rand':f'{rand}',
            't':f'{t}', 
            'roleType':'',
            'service':'http://tycgs.nankai.edu.cn/User/LoginCas', 
            'loginType':'0'
            }
    #r = requests.post('https://sso.nankai.edu.cn/sso/login', headers=hd3, cookies=cookie,data=info2, allow_redirects=False)
    r = session.post('https://sso.nankai.edu.cn/sso/login', headers=hd3, data=info2,
                    allow_redirects=False, 
                    verify=ver)
    print('\nstep 3  /sso/login:', r.text, r.status_code)
    time.sleep(0.4)

    # step 4 get the redirect
    h4 = """
        Host: tycgs.nankai.edu.cn
        Upgrade-Insecure-Requests: 1
        User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5672.127 Safari/537.36
        Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7
        Accept-Encoding: gzip, deflate
        Accept-Language: zh-CN,zh;q=0.9
        Connection: close
    """
    hd4 = parse_headers(h4)
    redirect_url = 'http://tycgs.nankai.edu.cn/User/LoginCas?ticket='
    try:
        ticket = r.json()['message']
        redirect_url = redirect_url + ticket
    except:
        ticket = None
        print('redirect_url is not valid')

    for _ in range(3):
        r = session.post(redirect_url, headers=hd4, allow_redirects=False)
        if r.status_code == 200 or r.status_code == 302:
            break
        time.sleep(1)


    print('\nstep 4  /User/LoginCas?ticket=:', ticket[:10],'... ',r.status_code)


    res = session.cookies.get_dict()
    res['username'] = username
    dump_cookies(res)
    if 'MYSELF_SESSION' in res and 'JWTUserToken' in res and 'UserId' in res:
        print('\nEof  successfully get_sso_jwt()')
        return res
    else:
        print("检查密码，或者重新")
        return None
    
if __name__ == '__main__':
    # 2111917
    # 2574474201aA
    p = get_sso_jwt(username='2111917', password='2574474201aA')
    print('\n\ncurrent session cookies:')
    for k, v in p.items():
        print(f'\t{k}: {v}')
        