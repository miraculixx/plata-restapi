from __future__ import absolute_import

from django.conf.urls import url
from django.contrib.auth.models import User
from tastypie.exceptions import Unauthorized
from tastypie.utils import trailing_slash


def actionurls(self):
    urls = []
    for name, method in self.__class__.__dict__.iteritems():
        if hasattr(method, "is_auto_action"):

            actionName = name if not hasattr(method, "auto_action_name") \
                else method.auto_action_name

            if hasattr(method, "auto_action_url"):
                urls.append(
                    url(method.auto_action_url,
                        self.wrap_view(name),
                        name="api_action_%s" % actionName)
                )
            else:
                if not method.auto_action_static:
                    urls.append(
                        url(r"^(?P<resource_name>%s)/(?P<%s>[A-Za-z0-9]+)/%s%s$" % (
                            self._meta.resource_name,
                            self._meta.detail_uri_name,
                            actionName,
                            trailing_slash()),
                            self.wrap_view(name),
                            name="api_action_static_%s" % actionName)
                    )
                else:
                    urls.append(
                        url(r"^(?P<resource_name>%s)/%s%s$" % (
                            self._meta.resource_name,
                            actionName,
                            trailing_slash()),
                            self.wrap_view(name),
                            name="api_action_%s" % actionName)
                    )
    return urls


def action(name=None,
           allowed=['get', 'post', 'put', 'patch', 'delete'],
           require_loggedin=False,
           static=False,
           url=None):
    def wrap(method):
        def dispatch(self, request, *args, **kwargs):
            # standard tastypie processing, see Resource.dispatch()
            self.method_check(request, allowed=allowed)
            if require_loggedin:
                self.is_authenticated(request)
            self.throttle_check(request)
            res = method(self, request, *args, **kwargs)
            return res
        # setup dispatch method 
        dispatch.is_auto_action = True
        dispatch.auto_action_static = static
        if not name is None:
            dispatch.auto_action_name = name
        if not url is None:
            dispatch.auto_action_url = url
        return dispatch
    return wrap
