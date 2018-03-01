from django.conf.urls import url
from apps.cart.views import AddView, CartView, UpdateView, DeleteView

urlpatterns = [

    url(r'^add$', AddView.as_view(), name='add'),  #购物车记录添加
    url(r'^update$', UpdateView.as_view(), name='update'), #购物车更新
    url(r'^delete$', DeleteView.as_view(), name='delete'), #购物车删除
    url(r'^$', CartView.as_view(), name='cartshow'),  #购物车展示
]
