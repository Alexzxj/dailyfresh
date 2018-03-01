from celery import Celery
from django.core.mail import send_mail
from django.conf import settings
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
app = Celery('celery_tasks.tasks', broker='redis://192.168.115.134:6379/0')
django.setup()

from apps.goods.models import IndexPromotionBanner, GoodsType, IndexTypeGoodsBanner, IndexGoodsBanner
# 发送邮件
@app.task
def celery_send_mail(username, content, email):
    # 发送邮件　　　/user/active/user_id
    subject = '天天生鲜'
    message = ''
    html_message = '<h1>%s,欢迎成为天天生鲜会员</h1>, 激活链接请点击<br><a href="http://192.168.115.134:8080/user/active/%s">http://192.168.115.134:8080/user/active/%s</a>' % (
    username, content, content)
    # message = '<h1>%s,欢迎成为天天生鲜会员</h1>, 激活链接请点击<br><a href="http://127.0.0.1:8888/user/active/%s">http://127.0.0.1:8888/user/active/%s</a>'%(username, content, content)
    sender = settings.EMAIL_FROM
    recipient_list = [email]
    send_mail(subject, message, sender, recipient_list, html_message=html_message)

# 产生静态页面
@app.task
def generate_static_html():
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

    # 加载模板
    from django.template import loader
    t1 = loader.get_template('index_static.html')
    # 渲染模板
    html = t1.render(context)

    save_path = os.path.join(settings.BASE_DIR, 'static/index1.html')
    with open(save_path, 'w')as f:
        f.write(html)



