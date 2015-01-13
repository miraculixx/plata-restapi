from django.http import HttpResponse
import paypalrestsdk
from plata.payment.modules.base import ProcessorBase
import tastypie
from tastypie.authorization import Authorization, DjangoAuthorization
from tastypie.bundle import Bundle
from tastypie.resources import Resource, ModelResource
from tastypie import fields
from plata.shop.models import *
from django.contrib.auth.models import User
from tastypie.resources import Resource
from tastypie import fields
import platarestapi
from platarestapi.actions import actionurls, action
from platarestapi.paypal import *
from platarestapi.utils import *
from tastypie.authentication import ApiKeyAuthentication, BasicAuthentication, MultiAuthentication


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


class PaymentResource(ModelResource):
    '''
    python manage.py syncdb to create new table for ApiKeyAuthentication
    ?username=admin&api_key=53bf26edd8fc0252db480c746cfe995e1facb928
    Or 
    Authorization: ApiKey admin:53bf26edd8fc0252db480c746cfe995e1facb928
    '''
    # order = fields.ForeignKey(OrderResource, 'order')
    def obj_create(self, bundle, **kwargs):
        """

        {
            "order_id": 5,
            "authorization": {
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
                    },
            "method": "paypal-rest-single"
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
        print bundle.request.body
        print json.loads(bundle.request.body)
        data = json.loads(bundle.request.body)
        order_id = data.get("order_id")
        method = data.get("method")
        authorization = data.get("authorization")
        order = Order.objects.get(pk=order_id)
        if method == 'paypal-rest-single':

            single_payment = SinglePaymentProcessor(1)
            new_payment = single_payment.create_pending_payment(order)
            new_payment.data['capture'] = {'order_id' : order_id , 'authorization' : authorization , 'method' : 'paypal-rest-single'}
            new_payment.save()
        else:
            future_payment = FuturePaymentProcessor(1)
            new_payment = future_payment.create_pending_payment(order)
            new_payment.data['capture'] = {'order_id' : order_id , 'authorization' : authorization , 'method' : 'paypal-rest-future'}
            new_payment.save()
        bundle.obj = new_payment
        return bundle


    def prepend_urls(self):
        return actionurls(self)

    @action(name='verify', allowed=['get'], require_loggedin=True)
    def verify(self, request, **kwargs):
        '''
        /api/v1/payment/1/verify/?username=admin&api_key=53bf26edd8fc0252db480c746cfe995e1facb928
        '''
        pk = kwargs['pk']
        payment = OrderPayment.objects.get(pk=pk)
        message = ''
        try:
            if payment.data.get('capture'):
                result, message = verify_payment(payment, user=request.user)
            else:
                return JsonResponse({"status": "failed", "msg": "need paypal authorization to verify the payment"}, 400)
        except Exception, e:
            return JsonResponse({"status": "failed", "msg": str(e)})
        return JsonResponse({"status": "success", "msg": message})

    # @action(allowed=['put'], require_loggedin=True)
    @action(allowed=['post'])
    def capture(self, request, **kwargs):
        '''
        /api/v1/payment/1/capture/?username=admin&api_key=53bf26edd8fc0252db480c746cfe995e1facb928
        {
            'correlationid' : <correlation id>
        }
        '''
        pk = kwargs['pk']
        payment = OrderPayment.objects.get(pk=pk)
        future_payment = FuturePaymentProcessor(1)
        return future_payment.process_order_confirmed(request, payment.order)

    @action(allowed=['post'])
    def approval(self, request, **kwargs):
        '''
        /api/v1/payment/1/approval/?username=admin&api_key=53bf26edd8fc0252db480c746cfe995e1facb928
        {
            "response": {
                "code": "EGZU4qcUF7hBLSzo4toZ5QlKwNR7dXbookRNvVhATn_l-EJNj1b3naxqZBbryG4F3ujWqf3a7TmM-bfA1v21S9Vptnj_VYV51FJTEZtCn0E-ZF2YgKeYmyw60W8d1xAePUt4c0zbYhRrSRiDgdnoQJ4"
            },
            "client": {
                "platform": "Android",
                "paypal_sdk_version": "2.7.1",
                "product_name": "PayPal-Android-SDK",
                "environment": "sandbox"
            },
            "response_type": "authorization_code"
        }
        '''
        user = request.user
        body = json.loads(request.body)
        auth_code = body['response']['code']
        print auth_code
        try:

            refresh_token = api.get_refresh_token(auth_code)
            print refresh_token
        except Exception, e:
            print str(e)
            return JsonResponse({"status": "fail", "msg": str(e)})
        print user
        user = User.objects.get(username=request.GET.get('username'))
        if PaymentAuthorization.objects.filter(user=user):
            payment_authorization = PaymentAuthorization.objects.filter(user=user).first()
            payment_authorization.access_token = auth_code
            payment_authorization.refresh_token = refresh_token
            payment_authorization.save()
            print payment_authorization
        else:
            payment_authorization = PaymentAuthorization(user=user)
            payment_authorization.access_token = auth_code

            payment_authorization.refresh_token = refresh_token
            payment_authorization.save()
            print payment_authorization
        return JsonResponse({"status": "success", "auth_code": auth_code})

    def obj_update(self, bundle, skip_errors=False, **kwargs):
        '''
        /api/v1/payment/1/?username=admin&api_key=53bf26edd8fc0252db480c746cfe995e1facb928
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
        }


        android create avd --name Default --target android-19 --abi armeabi-v7a
        '''
        pk = kwargs['pk']
        payment = OrderPayment.objects.get(pk=pk)
        body = json.loads(bundle.request.body)
        data = payment.data

        data['capture'] = {'order_id' : payment.order.id , 'authorization' : body , 'method' : 'paypal-rest-single'}
        if body.get('response_type') == 'payment':
            payment.transaction_id = body.get('response').get('id', '')

        payment.data = data
        payment.save()
        bundle.obj = payment
        return bundle

    class Meta:
        queryset = OrderPayment.objects.all()
        resource_name = 'payment'
        authorization = DjangoAuthorization()
        authentication = ApiKeyAuthentication()
        excludes = ['notes', 'status', 'authorized']
        always_return_data = True