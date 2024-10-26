### 1.获得tycgs.nankai sso token的流程


访问通过 `http://tycgs.nankai.edu.cn` 下的所有Api 都需要认证信息，其中必要的cookie信息是如下三个键值对：

~~~
'ASP.NET_SessionId': 'z52ivhk*****',
'JWTUserToken': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJu****',
'UserId': '94808953-5209-495d-aafc-*****',
~~~



#### 获得认证信息的过程：

1. 获得 **ssrf令牌**： `_lt`   ，**后面要用**

   访问`https://sso.nankai.edu.cn/sso/login?service=http://tycgs.nankai.edu.cn/User/LoginCas`=即可以获得（原页面html页面中搜索  `var _lt`）

   

2. 获得一个rand值: `rand `，**后面要用**

   继续使用步骤1的session，访问`https://sso.nankai.edu.cn/sso/loadcode` ，将返回json格式的报文，拿到其中报文中的 rand 字段即可

3. (可以跳过) 检查用户信息是否异常

   `https://sso.nankai.edu.cn/sso/checkRole`

4. (可以跳过) 检查weak?

   `https://sso.nankai.edu.cn/sso/checkWeak`

5. 拿到一个 叫做 `ticket` 的变量

   继续使用先前的session，并且post请求`https://sso.nankai.edu.cn/sso/login`， 并且请求体如下格式：

   ~~~python
   info2 = {'ajax':'1',
            'username':{username}, 
            'password':{password}, 
            'lt':f'{_lt}',
            'rand':f'{rand}',
            't':f'{t}', 
            'roleType':'',
            'service':'http://tycgs.nankai.edu.cn/User/LoginCas', 
            'loginType':'0'
           }
   ~~~

   注意其中的 `_lt`和`rand`变量在 1、2 两步已经拿到，t的获得是通过浏览器段根据用户密码获得一串字符，但经过测试，可以把t随便填写。`username`是自己学号，`password`是md5 哈希后的字符串。

   ~~~python
   # 哈希代码
   md5_hash = hashlib.md5()
   md5_hash.update(password.encode('utf-8'))
   return md5_hash.hexdigest()
   ~~~

   post成功后，服务器会返回一段json报文，拿到其中报文的 `message` 字段, 起名字`ticket`

6. 获得最后的认证信息

   访问 `http://tycgs.nankai.edu.cn/User/LoginCas?ticket=`{ticket}，返回的报头中`Set-Cookie`中即含有 `JWTUserToken` 等认证信息的键值。

