

### 1、请求数据解析

通过向`../../Field/GetVenueStateNew ` 发送get请求

#### （1）request

**请求的url类似**：

> http://tycgs.nankai.edu.cn/Field/GetVenueStateNew?dateadd=2&TimePeriod=0&VenueNo=003&FieldTypeNo=JNYMQ&_=1715610158790

cookies部分：

> ASP.NET_SessionId=ohjqh5tpdozt0bk2chf0q20m; 
>
> LoginSource=1;
>
>  LoginType=1; 
>
> NetId=; 		
>
> JWTUserToken=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJuYW1lIjoiOTQ4MDg5NTMtNTIwOS00OTVkLWFhZmMtZjhlNTVlY2I4Zjk0IiwiZXhwIjoxNzE2MTk5NTAzLjAsImp0aSI6ImxnIiwiaWF0IjoiMjAyNC0wNS0xMyAyMjowNTowMiJ9.ccAJbXofDaXflaYxS1oAJRQwpUrpacuDUGknLYuyvz0; 
>
> UserId=94808953-5209-495d-aafc-f8e55ecb8f94

**数据部分**：

- `dateadd`代表界面可选择的四个日期，如图：周一`DateAdd`字段为0，周四为3
- `TimePeriod` 始终 0
- `VenueNo` 始终为  003 （代表津南体育馆）
-  `FieldTypeNo`始终为  JNYMQ



![image-20240513225429733](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20240513225429733.png)

#### （2）reponse

一个json数据，其中的‘resultdata ’ 字段包含当前界面各个场地是否已被购买的状态。

大概这样子：

![image-20240513225927162](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20240513225927162.png)

其中`FieldState == 0` 并且  `TimeStatus == 1 ` 对应当前场地当前时间空闲，可以买。对应如下js代码

~~~js
	function getField():
			$("#loadingdiv").show();
            var strul = '';
            $.ajax({
                url: "../../Field/GetVenueStateNew",
                data: {
                    dateadd: DateAdd,
                    TimePeriod: TimePeriod,
                    VenueNo: VenueNo,
                    FieldTypeNo: FieldTypeNo
                },
                cache: false,
                success: function (data) {
                    var strdtfield = '';
                    var strultime = '';
~~~



![image-20240513224551243](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\image-20240513224551243.png)



### 3、购买

点击`确认预定`按钮，触发方法`comfirmsubmit()` ,最后触发`submit()`函数

向`../../Field/OrderField`发出get请求

#### （1）request 类似这样

~~~gas
GET http://tycgs.nankai.edu.cn/Field/OrderField?checkdata=[{"FieldNo":"JNYMQ002","FieldTypeNo":"JNYMQ","FieldName":"ç¾½02","BeginTime":"11:00","Endtime":"12:00","Price":"5.00"},{"FieldNo":"JNYMQ003","FieldTypeNo":"JNYMQ","FieldName":"ç¾½03","BeginTime":"11:00","Endtime":"12:00","Price":"5.00"}]&dateadd=3&VenueNo=003
~~~

- `checkdata`是一个列表，里面每一个{} 为一个场地购买项 注意FieldName gbk编码后为：羽02 羽03
- `dateadd`即代表日期
- `VenueNo` 003代表津南体育管

~~~js
 function submit() {
            $.weui.closeDialog();
            var objJson = [];
            ...
            
           objJson.push(jQuery.parseJSON('{"FieldNo":"' + FieldNo + '","FieldTypeNo":"' + FieldTypeNo + '","FieldName":"' + FieldName + '","BeginTime":"' + BeginTime + '","Endtime":"' + endtime + '","Price":"' + price + '"}'));
            });
            var str_json = JSON.stringify(objJson);
            isSubmitting = true;

			$.ajax({
                url: '../../Field/OrderField', //目标地址
                data: { checkdata: str_json, dateadd: DateAdd, VenueNo: VenueNo },
                success: function (data) {
                    isSubmitting = false;
                    $("#atj").text("确认预订");
                    var msgJson = $.parseJSON(data)
~~~





#### （2）reponse 得到一个json结果

`type`则表示成功， `resultdata` 为订单页面

{"IsCardPay":null,"MemberNo":null,"Discount":null,"ConType":null,"type":1,"errorcode":0,"message":"","resultdata":"9c0034e5-d52f-4bad-b467-34ad6241d190"}



### 3、访问订单页面付钱

#### （1）request

**url**: http://tycgs.nankai.edu.cn/Views/Pay/PayField.html?OID=9c0034e5-d52f-4bad-b467-34ad6241d190&VenueNo=003 
	**cookies**:

> Cookie: ASP.NET_SessionId=ohjqh5tpdozt0bk2chf0q20m; 
>
> LoginSource=1; 
>
> LoginType=1;
>
>  NetId=; JWTUserToken=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJuYW1lIjoiNGEwN2VmMWYtODJmMC00NjAzLWJiNmYtMmNkZGE1N2EyZDc4IiwiZXhwIjoxNzE2MjA4MjY2LjAsImp0aSI6ImxnIiwiaWF0IjoiMjAyNC0wNS0xNCAwMDozMTowNSJ9.DNw62yl9NvFYKS429qbjQQlgvdgiO0Mzg0UkCV8v_Ow; 
>
> UserId=4a07ef1f-82f0-4603-bb6f-2cdda57a2d78



即同OiD就可以得到支付界面



