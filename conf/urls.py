import os
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.shortcuts import redirect

from shop.views import shop
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'', include(shop.urls)),
    url(r'^$', lambda request: redirect('plata_product_list')),
    url(r'^products/$', 'shop.views.product_list',
        name='plata_product_list'),
    url(r'^products/(?P<object_id>\d+)/$', 'shop.views.product_detail',
        name='plata_product_detail'),

    # url(r'^reporting/', include('plata.reporting.urls')),

    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': os.path.join(os.path.dirname(__file__), 'media/')}),
)

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()
