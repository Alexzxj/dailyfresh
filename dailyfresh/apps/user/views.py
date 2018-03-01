import re
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from django.conf import settings
from django.core.mail import send_mail
from itsdangerous import SignatureExpired
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.http import HttpResponse
from apps.order.models import OrderGoods, OrderInfo
from apps.goods.models import GoodsSKU
from apps.user.models import User, Address
from celery_tasks.tasks import celery_send_mail
from django.contrib.auth import authenticate, login, logout
from utils.mixin import LoginRequestView, LoginRquestMixin
from django_redis import get_redis_connection
from django.core.paginator import Paginator


# Create your views here.
# user/register
def register(request):
    if request.method == 'GET':
        return render(request, 'register.html')
    else:
        # 接受数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        password2 = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 校验
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': "输入数据不完整"})

        # 邮箱校验
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': "邮箱不合法"})

        # 协议判断
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': "请勾选协议"})

        # 判断密码一致性
        if password != password2:
            return render(request, 'register.html', {'errmsg': "密码不一致"})
        # 判断用户名是否存在
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        if user:
            return render(request, 'register.html', {'errmsg': "用户名已注册"})
        # 业务处理
        user = User.objects.create_user(username, password, email)
        user.is_active = 0
        user.save()
        # 返回请求
        return redirect(reverse('goods:index'))

def register_handle(request):
    '''注册处理'''
    # 接受数据
    username = request.POST.get('user_name')
    password = request.POST.get('pwd')
    password2 = request.POST.get('cpwd')
    email = request.POST.get('email')
    allow = request.POST.get('allow')

    # 校验
    if not all([username, password, email]):
        return render(request, 'register.html', {'errmsg': "输入数据不完整"})

    # 邮箱校验
    if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
        return render(request, 'register.html', {'errmsg': "邮箱不合法"})

    # 协议判断
    if allow != 'on':
        return render(request, 'register.html', {'errmsg': "请勾选协议"})

    # 判断密码一致性
    if password != password2:
        return render(request, 'register.html', {'errmsg': "密码不一致"})
    # 判断用户名是否存在
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = None
    if user:
        return render(request, 'register.html', {'errmsg': "用户名已注册"})
    # 业务处理
    user = User.objects.create_user(username, password, email)
    user.is_active = 0
    user.save()
    # 返回请求
    return redirect(reverse('goods:index'))

class RegisterView(View):
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 接受数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        password2 = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 校验
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': "输入数据不完整"})

        # 邮箱校验
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': "邮箱不合法"})

        # 协议判断
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': "请勾选协议"})

        # 判断密码一致性
        if password != password2:
            return render(request, 'register.html', {'errmsg': "密码不一致"})
        # 判断用户名是否存在
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        if user:
            return render(request, 'register.html', {'errmsg': "用户名已注册"})
        # 业务处理
        user = User.objects.create_user(username=username, password=password, email=email)
        user.is_active = 0
        user.save()
        # 发送邮件　　　/user/active/user_id
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {"confirm": user.id}
        # 加密为一个bytes类型的，因此需要转换为str
        content = serializer.dumps(info).decode()

        # subject, message, from_email, recipient_list,
        # fail_silently = False, auth_user = None, auth_password = None,
        # # connection = None, html_message = None
        # subject = '天天生鲜'
        # message = ''
        # html_message = '<h1>%s,欢迎成为天天生鲜会员</h1>, 激活链接请点击<br><a href="http://127.0.0.1:8888/user/active/%s">http://127.0.0.1:8888/user/active/%s</a>'%(username, content, content)
        # # message = '<h1>%s,欢迎成为天天生鲜会员</h1>, 激活链接请点击<br><a href="http://127.0.0.1:8888/user/active/%s">http://127.0.0.1:8888/user/active/%s</a>'%(username, content, content)
        # sender = settings.EMAIL_FROM
        # recipient_list = [email]
        # send_mail(subject, message, sender, recipient_list, html_message=html_message)
        celery_send_mail.delay(username, content, email)
        # 返回请求
        return redirect(reverse('goods:index'))

class ActiveView(View):
    def get(self, request, token):
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
        except SignatureExpired:
            return HttpResponse("链接过期")
        return redirect(reverse('goods:index'))

class LoginView(View):
    def get(self, request):
        if 'username' in request.COOKIES:
            username = request.COOKIES['username']
            checked = 'checked'
        else:
            username = ''
            checked = ''

        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        # 接收参数
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        remember = request.POST.get('remember')
        # 参数校验
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '参数不完整'})

        # 业务处理
        user = authenticate(username=username, password=password)
        # print("------------", user)
        if user is not None:
            # 正确
            if user.is_active:
                login(request, user)
                next_url = request.GET.get('next', reverse('goods:index'))
                response = redirect(next_url)
                if remember == 'on':
                    # 记住用户名，cookie保存
                    response.set_cookie('username', username, max_age=7*24*3600)
                else:
                    response.delete_cookie('username')
                return response
            else:
                return render(request, 'login.html', {'errmsg': '用户未激活'})

        else:
            # username or password error
            return render(request, 'login.html', {'errmsg': '用户名或者密码错误'})
        # 返回响应

class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect(reverse('goods:index'))

# class UserCenterInfoView(View):
# class UserCenterInfoView(LoginRequestView):
class UserCenterInfoView(LoginRquestMixin, View):
    # 用户中心页－－用户详情
    def get(self, request):
        user = request.user
        # print(UserCenterInfoView.__mro__)
        # 获取用户的信息
        addr = Address.objects.get_default_address(user)
        # 获取用户的历史浏览记录
        # from redis import StrictRedis
        # conn = StrictRedis(host='192.168.115.134', port=6379, db=1)
        conn = get_redis_connection('default')
        user_key = 'history_user_%s'%user.id
        sku_ids = conn.lrange(user_key, 0, 4)
        # 方法一
        # skus = GoodsSKU.objects.filter(id__in=sku_ids)
        # history_list = []
        # for sku_id in sku_ids:
        #     for sku in skus:
        #         if int(sku_id) == sku:
        #             history_list.append(sku_id)
        # 方法二
        skus = []
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            skus.append(sku)
        context = {
            'skus': skus,
            'page': 'user',
            'addr': addr,

        }

        # return render(request, 'user_center_info.html', {'page': 'user', 'addr': addr})
        return render(request, 'user_center_info.html', context)

# class UserCenterAddrView(View):
# class UserCenterAddrView(LoginRequestView):
class UserCenterAddrView(LoginRquestMixin, View):
    # 用户中心页－－用户地址
    def get(self, request):
        user = request.user
        # 管理器模型类
        # try:
        #     addr = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     addr = None
        addr = Address.objects.get_default_address(user)

        return render(request, 'user_center_site.html', {'page': 'address', 'addr': addr})

    def post(self, request):
        # 获取参数
        receiver = request.POST.get('receiver')
        address = request.POST.get('address')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        # 参数校验
        if not all([receiver, address, zip_code, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '参数不完整'})
        # 业务处理 (加入地址)
        # 如果没有默认地址，则添加的为默认地址，否则不是默认地址　
        # is_default是否为ture
        user = request.user
        # 管理器模型类
        # try:
        #     addr = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     addr = None
        addr = Address.objects.get_default_address(user)
        is_default = True
        if addr:
            is_default = False
        Address.objects.create(
            user=user,
            receiver=receiver,
            addr=address,
            zip_code=zip_code,
            phone=phone,
            is_default=is_default
        )
        # 返回应答
        return redirect(reverse('user:address'))

# class UserCenterOrderView(View):
# class UserCenterOrderView(LoginRequestView):
class UserCenterOrderView(LoginRquestMixin, View):
    # 用户中心页－－用户订单
    def get(self, request, page):
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')
        for order in orders:
            order_goods = OrderGoods.objects.filter(order=order)
            for good in order_goods:
                amount = good.price * good.count
                good.amount = amount
            order.order_goods = order_goods
            # 支付状态名称
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            order.total_pay = order.total_price + order.transit_price

        # 获取分页的对象
        paginator = Paginator(orders, 1)
        page = int(page)
        if page > paginator.num_pages or page < 0:
            page = 1
        page_orders = paginator.page(page)

        # 页码显示
        num = paginator.num_pages
        if num < 5:
            pages = range(1, num + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num - page <= 2:
            pages = range(num - 4, num + 1)
        else:
            pages = range(page - 2, page + 3)

        context = {
            'page_orders': page_orders,
            'pages': pages,
            'page': 'order',
        }
        return render(request, 'user_center_order.html', context)




