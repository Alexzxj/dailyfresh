from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.views.generic import View
from apps.goods.models import IndexPromotionBanner, GoodsType, IndexTypeGoodsBanner, IndexGoodsBanner
from django_redis import get_redis_connection
from django.core.cache import cache
from apps.goods.models import GoodsSKU, Goods, GoodsType
from apps.order.models import OrderGoods

# Create your views here.
# 127.0.0.1:8888
class IndexView(View):
    # def index(request):
    #     return render(request, 'index1.html')
    def get(self, request):
        context = cache.get('static_html_cache')
        if context is None:
            # print("===3333======")
            # 获取商品分类信息
            goods_type = GoodsType.objects.all()
            # 获取商品轮播信息
            goods_banner = IndexGoodsBanner.objects.all().order_by('index')
            # 获取促销活动的产品信息
            promotion_banner = IndexPromotionBanner.objects.all().order_by('index')
            # 获取商品分类的详细信息
            for good in goods_type:
                title_banner = IndexTypeGoodsBanner.objects.filter(type=good, display_type=0).order_by('index')
                image_banner = IndexTypeGoodsBanner.objects.filter(type=good, display_type=1).order_by('index')

                good.title_banner = title_banner
                good.image_banner = image_banner

            # 获取购物车的信息'
            cart_count = 0
            context = {
                'goods_type': goods_type,
                'goods_banner': goods_banner,
                'promotion_banner': promotion_banner,
                'cart_count': cart_count,
            }
            cache.set('static_html_cache', context, 3600)

        user = request.user
        cart_count = 0
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)
        context.update(cart_count=cart_count)
        return render(request, 'index.html', context)

# 商品详情页
class DetailView(View):
    def get(self, request, sku_id):
        # 获取商品详情
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))
        # 获取商品的分类
        goods_type = GoodsType.objects.all()
        # 获取新品
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]
        # 获取相同规格的商品
        same_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=sku.id)
        # 获取评论
        order_skus = OrderGoods.objects.filter(sku=sku).exclude(comment='').order_by('-update_time')
        # 购物车数量
        user = request.user
        cart_count = 0
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)
            # 添加历史浏览记录
            user_key = 'history_user_%s' % user.id
            # 删除相同的记录
            conn.lrem(user_key, 0, sku_id)
            # 添加记录
            conn.lpush(user_key, sku_id)
            # 保留最多五个
            conn.ltrim(user_key, 0, 4)

        context = {
            'sku': sku,
            'goods_type': goods_type,
            'new_skus': new_skus,
            'same_skus': same_skus,
            'order_skus': order_skus,
            'cart_count': cart_count
        }
        return render(request, 'detail.html', context)

# 商品列表页
# /list/type_id/page?sort=xx
class ListView(View):
    def get(self, request, type_id, page):
        # 根据ｉｄ获取商品的分类信息
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return redirect(reverse('goods:index'))
        # 获取所有的分类信息
        goods_type = GoodsType.objects.all()
        # 获取相同的新品信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]
        # 根据排序方式进行排序
        sort = request.GET.get('sort', 'default')
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')
        # 获取分页的对象
        paginator = Paginator(skus, 1)
        page = int(page)
        if page > paginator.num_pages or page < 0:
            page = 1
        page_skus = paginator.page(page)

        # 页码显示
        num = paginator.num_pages
        if num < 5:
            pages = range(1, num+1)
        elif page <= 3:
            pages = range(1, 6)
        elif num - page <= 2:
            pages = range(num-4, num+1)
        else:
            pages = range(page-2, page+3)


        # 获取购物车条目数
        user = request.user
        cart_count = 0
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)
        context = {
            'type': type,
            'goods_type': goods_type,
            'new_skus': new_skus,
            'page_skus': page_skus,
            'cart_count': cart_count,
            'sort': sort,
            'pages': pages,
        }
        return render(request, 'list.html', context)