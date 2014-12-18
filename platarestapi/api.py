from django.http import HttpResponse
import paypalrestsdk
from tastypie.authorization import Authorization
from tastypie.bundle import Bundle
from tastypie.resources import Resource, ModelResource
from tastypie import fields
from plata.shop.models import *
from django.contrib.auth.models import User
from tastypie.resources import Resource
from tastypie import fields
import platarestapi
from platarestapi.actions import actionurls, action
from platarestapi.paypal import PaymentProcessor
from platarestapi.utils import *


class BucketObject(object):
    """
    Container to keep data that doesn't conform to any orm model, but has to be returned
    by some resources.
    """

    def __init__(self, initial=None):
        self.__dict__['_data'] = {}

        if hasattr(initial, 'items'):
            self.__dict__['_data'] = initial

    def __getattr__(self, name):
        return self._data.get(name, None)

    def __setattr__(self, name, value):
        self.__dict__['_data'][name] = value

    def to_dict(self):
        return self._data


class dict2obj(object):
    """
    Convert dictionary to object
    @source http://stackoverflow.com/a/1305561/383912
    """

    def __init__(self, d):
        self.__dict__['d'] = d

    def __getattr__(self, key):
        value = self.__dict__['d'][key]
        if type(value) == type({}):
            return dict2obj(value)

        return value


class CustomPaymentResource(Resource):
    id = fields.IntegerField(attribute='id')
    data = fields.CharField(attribute='data')

    class Meta:
        resource_name = 'payment'

    def obj_get(self, bundle, **kwargs):
        # bucket = self._bucket()
        pk = kwargs['pk']
        print kwargs['pk']
        return OrderPayment.objects.get(pk=int(pk))

    def obj_get_list(self, request=None, **kwargs):
        payments = []
        # your actual logic to retrieve contents from external source.

        # example
        payments.append(dict2obj(
            {
                'id': 1
            }
        ))
        payments.append(dict2obj(
            {
                'id': 2
            }
        ))

        return payments


class OrderResource(ModelResource):
    class Meta:
        queryset = Order.objects.all()
        resource_name = 'order'

import json

from paypalrestsdk import Capture, ResourceNotFound


class PaymentResource(ModelResource, PaymentProcessor):
    # order = fields.ForeignKey(OrderResource, 'order')
    def obj_create(self, bundle, **kwargs):
        """

        {
         "order_id": 1
        }

        :return:
        {
            "amount": "500.00",
            "currency": "USD",
            "data": "{}",
            "id": 1,
            "order_id": 1,
            "payment_method": "",
            "payment_module": "Paypal",
            "payment_module_key": "paypalrestapi",
            "resource_uri": "/api/v1/payment/1/",
            "timestamp": "2014-12-08T17:29:48.396668",
            "transaction_id": ""
        }
        """

        order_id = json.loads(bundle.request.body).get("order_id")
        order = Order.objects.get(pk=order_id)
        new_payment = self.create_pending_payment(order)
        bundle.obj = new_payment
        return bundle


    def prepend_urls(self):
        return actionurls(self)

    @action(name='verify', allowed=['get'])
    def verify(self, request, **kwargs):
        pk = kwargs['pk']
        payment = OrderPayment.objects.get(pk=pk)
        message = ''
        try:
            result, message = verify_payment(payment)
        except:
            pass
        return JsonResponse({"status": "success", "msg": message})

    @action(allowed=['put'], require_loggedin=True)
    def capture(self, request, **kwargs):
        print request
        pk = kwargs['pk']
        payment = OrderPayment.objects.get(pk=pk)
        return self.process_order_confirmed(request, payment.order)

    @action(allowed=['post'], static=True)
    def approval(self, request, **kwargs):
        pass

    def obj_update(self, bundle, skip_errors=False, **kwargs):
        '''
        {
            "response": {
                "state": "approved",
                "id": "PAY-8XS49767G4008033KKSJQG6Y",
                "create_time": "2014-12-18T16:40:27Z",
                "intent": "sale"
            },
            "client": {
                "platform": "Android",
                "paypal_sdk_version": "2.7.1",
                "product_name": "PayPal-Android-SDK",
                "environment": "sandbox"
            },
             "response_type": "payment"


        {
            "response": {
                "code": "ELv4d7jue8mm5WLgaEzgXSSO4XzLJgwXp3ZzKHTQSK7kWAKMTC1jMABmGfkswI-LOODL-i3ZPQmMujWRr6d6DibSBI1K3ZVujkqLmpiXr6h3YE-FpFU5X3nP-i7aN2K_n2xtMBpA5pe4idXp9cYjZuI"
                },
            "client": {
                "platform": "Android",
                "paypal_sdk_version": "2.7.1",
                 "product_name": "PayPal-Android-SDK",
                "environment": "sandbox"
            },
             "response_type": "authorization_code"
        }
        android create avd --name Default --target android-19 --abi armeabi-v7a
        '''
        print bundle.request
        pk = kwargs['pk']
        payment = OrderPayment.objects.get(pk=pk)
        body = json.loads(bundle.request.body)
        data = payment.data
        data["create"] = {
            "response": body
        }
        payment.transaction_id = body.get('response').get('id', '')
        payment.data = data
        payment.save()
        bundle.obj = payment
        return bundle

    class Meta:
        queryset = OrderPayment.objects.all()
        resource_name = 'payment'
        authorization = Authorization()
        excludes = ['notes', 'status', 'authorized']
        always_return_data = True
        # allowed_methods = ['get']
    # def hydrate(self, bundle):
    #     order = Order.objects.get(pk=4)
    #     bundle.obj.order = order
    #     bundle.obj.amount = order.total
    #     return bundle