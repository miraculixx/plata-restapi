import os
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.shortcuts import redirect
from tastypie.api import Api
from shop.views import shop
from platarestapi.api import *
from django.contrib import admin

admin.autodiscover()

v1_api = Api(api_name='v1')
v1_api.register(PaymentResource())
v1_api.register(OrderResource())
'''
/api/v1/payment/ POST

{
  "order_id": 1
}

/api/v1/payment/4/ DELETE
'''
urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'', include(shop.urls)),
    url(r'^$', lambda request: redirect('plata_product_list')),
    url(r'^products/$', 'shop.views.product_list',
        name='plata_product_list'),
    url(r'^products/(?P<object_id>\d+)/$', 'shop.views.product_detail',
        name='plata_product_detail'),

    # url(r'^reporting/', include('plata.reporting.urls')),
    url(r'^api/', include(v1_api.urls)),
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': os.path.join(os.path.dirname(__file__), 'media/')}),
)

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()
