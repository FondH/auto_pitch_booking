### 1.获得tycgs.nankai sso token的流程


发现南开体育的认证也升级和教务系统一致了，不过反而简化了爬虫的过程。想爬 `http://tycgs.nankai.edu.cn` 下的所有Api 都需要认证信息，其中必要的cookie信息是如下三个键值对：

~~~
'ASP.NET_SessionId': 'z52ivhk*****',
'JWTUserToken': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJu****',
'UserId': '94808953-5209-495d-aafc-*****',
~~~

#### 过程

1. Post 访问 'https://iam.nankai.edu.cn/api/v1/login?os=web' 获得一个session id（如下图response中报头），注意请求体是一段json，其中password是hash后的，具体的hash方法见1.1。

   ~~~
   {
   "login_scene":"feilian",
   "account_type":"userid",
   "account":"2111***",
   "password":"*****"
   }
   ~~~

   1. password hash方法：

      ~~~javascript
      function g(e) {
          const t = (r = Number.MAX_SAFE_INTEGER.toString(),
                     o().MD5(r).toString()).toString()
          , n = o().SHA1(o().enc.Utf8.parse(t));
          var r;
          return o().AES.encrypt(e, o().enc.Utf8.parse(t), {
              iv: o().enc.Utf8.parse(n.toString(o().enc.Hex)),
              mode: o().mode.CBC,
              padding: o().pad.Pkcs7
          }).ciphertext.toString(o().enc.Hex)
      }
      
      // zhuan
      ~~~

      

   ![image-20241015132008035](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241015132008035.png)

2. 拿步骤1的sessionid GET访问 /api/cas/login?service=http://tycgs.nankai.edu.cn/User/LoginCas&lang=en-US 

   ![image-20241015132340679](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241015132340679.png)

3. 进而在重定向的response 报文得到认证信息。

   ![image-20241015132228415](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20241015132228415.png)





