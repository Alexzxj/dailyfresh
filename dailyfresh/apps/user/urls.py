from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from apps.user.views import RegisterView, ActiveView, LoginView, LogoutView, UserCenterAddrView, UserCenterInfoView, UserCenterOrderView


urlpatterns = [
    # url(r'^register$', views.register, name='register'),
    # url(r'^register_handle$', views.register_handle, name='register_handle'),
    url(r'^register$', RegisterView.as_view(), name='register'),
    url(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),
    url(r'^login$', LoginView.as_view(), name='login'),
    url(r'^logout$', LogoutView.as_view(), name='logout'),
    # url(r'^order$', login_required(UserCenterOrderView.as_view()), name='order'),
    # url(r'^address$', login_required(UserCenterAddrView.as_view()), name='address'),
    # url(r'^$', login_required(UserCenterInfoView.as_view()), name='user'),
    url(r'^order/(?P<page>\d+)$', UserCenterOrderView.as_view(), name='order'),
    url(r'^address$', UserCenterAddrView.as_view(), name='address'),
    url(r'^$', UserCenterInfoView.as_view(), name='user'),
]
