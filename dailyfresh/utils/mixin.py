from django.contrib.auth.decorators import login_required
from django.views.generic import View

class LoginRequestView(View):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(LoginRequestView, cls).as_view(**initkwargs)
        return login_required(view)

class LoginRquestMixin(object):
    @classmethod
    def as_view(cls, **initkwargs):
        view = super(LoginRquestMixin, cls).as_view(**initkwargs)
        return login_required(view)
