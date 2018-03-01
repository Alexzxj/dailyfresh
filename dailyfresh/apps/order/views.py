import os
from django.conf import settings
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.views.generic import View
from utils.mixin import LoginRquestMixin
from apps.user.models import Address
from django_redis import get_redis_connection
from apps.goods.models import GoodsSKU
from django.http import JsonResponse
from apps.user.models import Address
from apps.order.models import OrderInfo, OrderGoods
from apps.goods.models import GoodsSKU
from datetime import datetime
from django.db import transaction
from alipay import AliPay

# Create your views here.

# 提交订单
# /order/place
class OrderPlaceView(LoginRquestMixin, View):
    def post(self, request):
        # 获取参数
        skus_id = request.POST.getlist('sku_id')
        # 参数校验
        if not all(skus_id):
            return redirect(reverse('cart:cartshow'))
        # 业务处理
        # 获取地址
        user = request.user
        addrs = Address.objects.filter(user=user)
        # 遍历
        cart_key = "cart_%s"%user.id
        conn = get_redis_connection('default')
        # 总件数
        total_count = 0
        # 总价
        total_price = 0
        # 运费
        trans_price = 0
        skus = []
        for sku_id in skus_id:
            sku = GoodsSKU.objects.get(id=sku_id)
            count = conn.hget(cart_key, sku_id)
            amount = sku.price * int(count)
            sku.count = int(count)
            sku.amount = amount
            total_count += int(count)
            total_price += amount
            skus.append(sku)
        # 运费表
        if total_price < 100:
            trans_price = 10
        elif total_price < 300:
            trans_price = 8
        elif total_price < 500:
            trans_price = 5
        else:
            trans_price = 0
        # 实付款
        total_pay = total_price + trans_price
        # 转换为字符串
        sku_ids = ','.join(skus_id)
        context = {
            'total_pay': total_pay,
            'total_count': total_count,
            'total_price': total_price,
            'trans_price': trans_price,
            'addrs': addrs,
            'skus': skus,
            'sku_ids': sku_ids,
        }
        # 返回应答
        return render(request, 'place_order.html', context)

# 订单创建
# ａｊａｘ　　　地址ｉｄ　支付方式　　商品ｉｄ
# /order/commit
class OrderCommitView1(View):
    @transaction.atomic
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # todo:获取参数
        sku_ids = request.POST.get('sku_ids')
        pay_method = request.POST.get('pay_method')
        addr_id = request.POST.get('addr_id')
        # print("======", sku_ids, pay_method, addr_id)
        # todo:参数校验
        if not all([sku_ids, pay_method, addr_id]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})
        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '地址不存在'})
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 4, 'errmsg': '支付方式有误'})
        # 转换为列表
        sku_ids = sku_ids.split(',')
        # 订单ｉｄ
        order_id = datetime.now().strftime('%Y%m%d%H%M%s') + str(user.id)
        # 总件数
        total_count = 0
        # 总价
        total_price = 0
        # 运费
        transit_price = 0
        # 设置保存点
        p1 = transaction.savepoint()
        # todo:业务处理
        # todo:向订单信息表中添加已条记录
        try:
            order_info = OrderInfo.objects.create(
                            order_id=order_id,
                            user=user,
                            addr=addr,
                            pay_method=pay_method,
                            total_count=total_count,
                            total_price=total_price,
                            transit_price=transit_price,
                        )
            # todo: 循环遍历商品列表
            conn = get_redis_connection('default')
            cart_key = 'cart_%s'%user.id
            for sku_id in sku_ids:
                try:
                    # sku = GoodsSKU.objects.get(id=sku_id)
                    print("wait lock",user.id)
                    import time
                    time.sleep(5)
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                    print("locking", user.id)
                except GoodsSKU.DoesNotExist:
                    transaction.savepoint_rollback(p1)
                    return JsonResponse({'res': 5, 'errmsg': '商品不存在'})
                # 获取商品数量和价格
                count = conn.hget(cart_key, sku_id)
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(p1)
                    return JsonResponse({'res': 7, 'errmsg': '商品库存不足'})
                # todo:向订单商品表中添加已条记录
                order_goods = OrderGoods.objects.create(
                                order=order_info,
                                sku=sku,
                                count=count,
                                price=sku.price,
                            )

                # todo:减少库存增加销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()
                # todo:累加总价格和总的数量
                total_count += int(count)
                total_price += sku.price * int(count)
            # todo:更新之前添加的总价，运费和总件数信息
            # 运费表
            if total_price < 100:
                transit_price = 10
            elif total_price < 300:
                transit_price = 8
            elif total_price < 500:
                transit_price = 5
            else:
                transit_price = 0
            order_info.total_price = total_price
            order_info.total_count = total_count
            order_info.transit_price = transit_price
            order_info.save()
            # todo:删除购物车记录
            conn.hdel(cart_key, *sku_ids)
        except Exception as e:
            transaction.savepoint_rollback(p1)
            return JsonResponse({'res': 8, 'msg': '订单创建失败'})

        # 返回应答
        return JsonResponse({'res': 6, 'msg': '订单创建成功'})

# 乐观锁
class OrderCommitView(View):
    @transaction.atomic
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # todo:获取参数
        sku_ids = request.POST.get('sku_ids')
        pay_method = request.POST.get('pay_method')
        addr_id = request.POST.get('addr_id')
        # print("======", sku_ids, pay_method, addr_id)
        # todo:参数校验
        if not all([sku_ids, pay_method, addr_id]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})
        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '地址不存在'})
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 4, 'errmsg': '支付方式有误'})
        # 转换为列表
        sku_ids = sku_ids.split(',')
        # 订单ｉｄ
        order_id = datetime.now().strftime('%Y%m%d%H%M%s') + str(user.id)
        # 总件数
        total_count = 0
        # 总价
        total_price = 0
        # 运费
        transit_price = 0
        # 设置保存点
        p1 = transaction.savepoint()
        # todo:业务处理
        # todo:向订单信息表中添加已条记录
        try:
            order_info = OrderInfo.objects.create(
                            order_id=order_id,
                            user=user,
                            addr=addr,
                            pay_method=pay_method,
                            total_count=total_count,
                            total_price=total_price,
                            transit_price=transit_price,
                        )
            # todo: 循环遍历商品列表
            conn = get_redis_connection('default')
            cart_key = 'cart_%s'%user.id
            for sku_id in sku_ids:
                for i in range(3):
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                        # print("wait lock",user.id)
                        # import time
                        # time.sleep(5)
                        # sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                        # print("locking", user.id)
                    except GoodsSKU.DoesNotExist:
                        transaction.savepoint_rollback(p1)
                        return JsonResponse({'res': 5, 'errmsg': '商品不存在'})
                    # 获取商品数量和价格
                    count = conn.hget(cart_key, sku_id)
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(p1)
                        return JsonResponse({'res': 7, 'errmsg': '商品库存不足'})
                    # todo:减少库存增加销量
                    origin_stock = sku.stock
                    new_stock = origin_stock - int(count)
                    new_sales = sku.sales + int(count)
                    # print('user_%d----time:%d----stock:%d' % (user.id, i, origin_stock))
                    # import time
                    # time.sleep(10)
                    # 查询并更新数据库，成功返回１，否则为０
                    res = GoodsSKU.objects.filter(id=sku_id, stock=origin_stock).update(sales=new_sales, stock=new_stock)
                    # print("====",res)
                    if res == 0:
                        if i == 2:
                            transaction.savepoint_rollback(p1)
                            return JsonResponse({'res': 9, 'errmsg': '库存更新有误'})
                        continue

                    # todo:向订单商品表中添加已条记录
                    order_goods = OrderGoods.objects.create(
                                    order=order_info,
                                    sku=sku,
                                    count=count,
                                    price=sku.price,
                                )
                    # todo:累加总价格和总的数量
                    total_count += int(count)
                    total_price += sku.price * int(count)
                    break
            # todo:更新之前添加的总价，运费和总件数信息
            # 运费表
            if total_price < 100:
                transit_price = 10
            elif total_price < 300:
                transit_price = 8
            elif total_price < 500:
                transit_price = 5
            else:
                transit_price = 0
            order_info.total_price = total_price
            order_info.total_count = total_count
            order_info.transit_price = transit_price
            order_info.save()
            # todo:删除购物车记录
            conn.hdel(cart_key, *sku_ids)
        except Exception as e:
            transaction.savepoint_rollback(p1)
            return JsonResponse({'res': 8, 'msg': '订单创建失败'})

        # 返回应答
        return JsonResponse({'res': 6, 'msg': '订单创建成功'})

# 支付宝支付
class OrderPayView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # 获取参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not all([order_id]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单信息错误'})
        # 业务处理　调用支付宝接口
        # 初始化
        alipay = AliPay(
            appid="2016082100304090",
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True,  # 默认False
        )
        # 调用接口　alipay.trade.page.pay
        total_amount = order.total_price + order.transit_price
        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,  # 订单id
            total_amount=str(total_amount),  # 订单总金额
            subject='天天生鲜%s' % order_id,  # 订单标题
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )
        # 返回应答
        pay_url = "https://openapi.alipaydev.com/gateway.do?" + order_string

        return JsonResponse({'res': 3, 'pay_url': pay_url})

# /order/check
class CkeckPayoffView(View):
    '''支付结果查询'''
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # 获取参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not all([order_id]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单信息错误'})
            # 业务处理　调用支付宝接口
        # 初始化
        alipay = AliPay(
            appid="2016082100304090",
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True,  # 默认False
        )
        # 调用交易查询函数
        # "alipay_trade_query_response": {
        #     "trade_no": "2017032121001004070200176844",
        #     "code": "10000",
        #     "invoice_amount": "20.00",
        #     "open_id": "20880072506750308812798160715407",
        #     "fund_bill_list": [
        #         {
        #             "amount": "20.00",
        #             "fund_channel": "ALIPAYACCOUNT"
        #         }
        #     ],
        #     "buyer_logon_id": "csq***@sandbox.com",
        #     "send_pay_date": "2017-03-21 13:29:17",
        #     "receipt_amount": "20.00",
        #     "out_trade_no": "out_trade_no15",
        #     "buyer_pay_amount": "20.00",
        #     "buyer_user_id": "2088102169481075",
        #     "msg": "Success",
        #     "point_amount": "0.00",
        #     "trade_status": "TRADE_SUCCESS",
        #     "total_amount": "20.00"
        # }
        while True:
            response = alipay.api_alipay_trade_query(out_trade_no=order_id)
            code = response.get('code')
            if code == '10000' and response.get('trade_status') == "TRADE_SUCCESS":
                order.trade_no = response.get('trade_no')
                order.order_status = 4
                order.save()
                return JsonResponse({'res': 3, 'msg': '支付成功'})
            elif (code == '40004') or (code == '10000' and response.get('trade_status') == "WAIT_BUYER_PAY"):
                import time
                time.sleep(5)
                continue
            else:
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})
