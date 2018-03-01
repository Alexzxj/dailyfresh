from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from apps.goods.models import GoodsSKU
from django_redis import get_redis_connection
from utils.mixin import LoginRquestMixin


# Create your views here.

# 添加购物车
# 前端使用Ａｊａｘ请求　　　参数sku_id   count
# /cart/add
class AddView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # 获取参数
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        # 参数校验
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'errmsg': '数目错误'})
        if count <= 0:
            return JsonResponse({'res': 4, 'errmsg': '数目不合法'})
        # 业务处理
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        # 先查询购物车中是否存在此商品
        sku_count = conn.hget(cart_key, sku_id)
        # 商品数量累加
        if sku_count:
            count += int(sku_count)
        # 判断库存
        if count > sku.stock:
            return JsonResponse({'res': 5, 'errmsg': '库存不足'})
        # 添加成功
        conn.hset(cart_key, sku_id, count)
        # 获取购物车中的总条目数
        total_count = conn.hlen(cart_key)
        # 返回应答
        return JsonResponse({'res': 6, 'total_count': total_count, 'msg': '添加成功'})

# 获取购物车记录
# /cart
class CartView(LoginRquestMixin, View):
    def get(self, request):
        user = request.user
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # 获取购物车所有的记录　　　
        # 返回为一个字典
        cart_dict = conn.hgetall(cart_key)
        skus = []
        total_count = 0
        total_price = 0
        # 遍历字典
        for sku_id, count in cart_dict.items():
            # 获取对应商品的对象
            sku = GoodsSKU.objects.get(id=sku_id)
            # 商品小计
            amount = int(count) * sku.price
            sku.amount = amount
            # 商品数量
            sku.count = count
            skus.append(sku)
            total_count += int(count)
            total_price += amount
        # 组织模板上下文
        context = {
            'skus': skus,
            'total_count': total_count,
            'total_price': total_price,
        }
        # 返回应发
        return render(request, 'cart.html', context)

# 更新购物车记录
# 前端使用Ａｊａｘ请求　　　参数sku_id   count
# /cart/update
class UpdateView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # 获取参数
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        # 参数校验
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 3, 'errmsg': '数目错误'})
        if count <= 0:
            return JsonResponse({'res': 4, 'errmsg': '数目不合法'})
        # 业务处理
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        # 判断库存
        if count > sku.stock:
            return JsonResponse({'res': 5, 'errmsg': '库存不足'})
        # 更新购物车
        conn.hset(cart_key, sku_id, count)
        vals = conn.hvals(cart_key)
        total_count = 0
        for val in vals:
            total_count += int(val)
        # 返回应答
        return JsonResponse({'res': 6, 'total_count': total_count, 'msg': '更新成功'})

# 删除购物车记录
# 前端使用Ａｊａｘ请求　　　参数sku_id
# /cart/delete
class DeleteView(View):
    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # 获取参数
        sku_id = request.POST.get('sku_id')

        # 参数校验
        if not all([sku_id]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

        # 业务处理
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        # 删除购物车
        conn.hdel(cart_key, sku_id)
        # 计算购物车中的总件数
        vals = conn.hvals(cart_key)
        total_count = 0
        for val in vals:
            total_count += int(val)
        # 返回应答
        return JsonResponse({'res': 3, 'total_count': total_count, 'msg': '更新成功'})

