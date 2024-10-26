from api.sso import parse_headers
from utils.cookie_control import dump_cookies
import requests
def get_sso_jwt(username, password='ca0d3ba5b76c0ae721a584225f8f8f1c'):
    # step0 get the ticket session
    session = requests.Session()
    session.cookies.update({
                               'session': 'MTcyODk2NjA5NnxOd3dBTkZGV1VqTTNXa1UyVkVoTlEwTlpTek5KVWpOQlIwbzNOa2xaVFU0eVJVa3pRVGRIV2taRlNGTkZUekkxVVVwTE56WlFRMUU9fLPZ-f2vy_gFpBjBPf31h6BJ43NHOOR4OCX6TH2X3bCv'})
    hd = """
    Host: iam.nankai.edu.cn
    Content-Length: 115
    X-Fe-Version: 3.0.3.5537
    Sec-Ch-Ua-Platform: "Windows"
    Accept-Language: en-US
    Sec-Ch-Ua: "Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"
    X-Version-Check: 0
    Csrf-Token: SUsCJUYcAqufvkzHWSOZWWBqBxqQIZOdHoEmiQy1
    Sec-Ch-Ua-Mobile: ?0
    User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36
    Content-Type: application/json
    Accept: */*
    Origin: https://iam.nankai.edu.cn
    Sec-Fetch-Site: same-origin
    Sec-Fetch-Mode: cors
    Sec-Fetch-Dest: empty
    Referer: https://iam.nankai.edu.cn/login?next=%2Fapi%2Fcas%2Flogin%3Fservice%3Dhttp%3A%2F%2Ftycgs.nankai.edu.cn%2FUser%2FLoginCas
    Accept-Encoding: gzip, deflate
    Priority: u=1, i
        """

    url = 'https://iam.nankai.edu.cn/api/v1/login?os=web'
    param = {
        "login_scene": "feilian",
        "account_type": "userid",
        "account": f"{username}",
        "password": f"{password}"
    }
    r = session.post(url, json=param, headers=parse_headers(hd), verify=True)
    session.cookies.clear()
    session.cookies.update(r.cookies)

    # step1 get ticket url
    url1 = 'https://iam.nankai.edu.cn/api/cas/login?service=http://tycgs.nankai.edu.cn/User/LoginCas&lang=en-US'
    r = session.get(url1, timeout=10, allow_redirects=False)
    redirect_ticket_url = ''
    for k,v in r.headers.items():
        if k == 'Location':
           redirect_ticket_url = v

    # step 2 访问redirct url 获得认知信息
    session.cookies.clear()
    session.cookies.update(r.cookies)
    r = session.get(redirect_ticket_url)
    for k,v in session.cookies.items():
        print(f'{k}:{v}')

    # step3 dump
    res = session.cookies.get_dict()
    res['username'] = username
    dump_cookies(res)
    if 'ASP.NET_SessionId' in res and 'JWTUserToken' in res and 'UserId' in res:
        print('\nEof successfully get_sso_jwt()')
        return res
    else:
        print("检查密码，或者重新")
        return None


