from django.conf.urls import url
from apps.order.views import OrderPlaceView, CkeckPayoffView, OrderCommitView, OrderPayView

urlpatterns = [

    url(r'^place$', OrderPlaceView.as_view(), name='place'),
    url(r'^commit$', OrderCommitView.as_view(), name='commit'),
    url(r'^pay$', OrderPayView.as_view(), name='pay'),  # 订单支付
    url(r'^check$', CkeckPayoffView.as_view(), name='CHECK'),  # 订单检查

]
