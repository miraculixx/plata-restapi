
import json

from plata.shop.models import Order, OrderPayment
from tastypie.authentication import ApiKeyAuthentication
from tastypie.authorization import DjangoAuthorization
from tastypie.resources import ModelResource

from platarestapi.actions import actionurls, action
from platarestapi.utils import JsonResponse, ShopUtil, api
from tastypie.exceptions import BadRequest
from platarestapi.processor.paypal.mixin import PaypalConstants


class OrderResource(ModelResource):
    class Meta:
        queryset = Order.objects.all()
        resource_name = 'order'


class PaymentResource(ModelResource):
    def prepend_urls(self):
        return actionurls(self)

    '''
    python manage.py syncdb to create new table for ApiKeyAuthentication
    ?username=admin&api_key=53bf26edd8fc0252db480c746cfe995e1facb928
    Or 
    Authorization: ApiKey admin:53bf26edd8fc0252db480c746cfe995e1facb928
    '''
    # order = fields.ForeignKey(OrderResource, 'order')
    def obj_create(self, bundle, **kwargs):
        """
        Create a payment
        
        This creates a pending payment in the shop system. It does not, however
        create a payment at the payment provider. The method parameter is any
        of the available payment modules:
        
        paypalrestapi-single -- for single payments
        paypalrestapi-future -- for future payments
        
        1. Retrieve processor for the given method
        2. Execute processor.process_order_confirmed method
        3. Prepare response
        
        :param order_id: the shop order id this payment refers to
        :param method: the payment method (processor) to use
        :param authorization: the payment provider's authorization data for
        this payment
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
        # get parameters
        order_id = bundle.data.get('order_id')
        method = bundle.data.get("method")
        authorization = bundle.data.get("authorization")
        order = Order.objects.get(pk=order_id)
        # start processing
        try:
            processor = self.shoputil.get_payment_processor(method)
        except:
            raise BadRequest('invalid payment method %s' % method)
        else:
            # create a pending order and return order data
            resp = processor.process_order_confirmed(bundle.request, 
                                  order, order_id, authorization)
            bundle.data = resp
            bundle.obj = processor.get_or_create_pending_payment(order)
        return bundle
    
    def obj_update(self, bundle, skip_errors=False, **kwargs):
        '''
        update a payment with authorization data
        
        this is the same as calling POST with the authorization parameter.
        Authorization data is required to process capture or verify actions.  
        
        :param pk: primary key of Paypal payment
        :param body: the authorization data 
        '''
        pk = kwargs['pk']
        payment = OrderPayment.objects.get(pk=pk)
        try:
            processor = self.shoputil.get_processor_by_payment(payment)
        except:
            raise BadRequest('invalid payment method %s' % 
                             payment.payment_module_key)
        # update payment with authorization data 
        authorization = bundle.data.get('authorization')
        resp = processor.process_order_confirmed(bundle.request, 
                                  payment.order, payment.order.id, authorization)
        bundle.data = resp
        # reload payment data as processed
        bundle.obj = OrderPayment.objects.get(pk=payment.pk)
        return bundle

    @action(name='verify', allowed=['get'], require_loggedin=True)
    def verify(self, request, **kwargs):
        '''
        verify a payment
        
        this returns success if the payment has been approved and
        transactions have been completed. Otherwise returns failed.
        '''
        pk = int(kwargs['pk'])
        payment = OrderPayment.objects.get(pk=pk)
        processor = self.shoputil.get_processor_by_payment(payment)
        message = ''
        result = False
        try:
            if payment.data.get('capture').get('authorization'):
                result, message = processor.verify_payment(payment, 
                                PaypalConstants.APPROVED, 
                                PaypalConstants.COMPLETED, user=request.user)
            else:
                return JsonResponse({"status": "failed", "msg": ("need paypal "
                            "authorization to verify the payment")}, status=400)
        except Exception, e:
            return JsonResponse({"status": "failed", "msg": str(e)}, status=400)
        return JsonResponse({"status": "success" if result 
                             else "failed", "msg": message})

    # @action(allowed=['put'], require_loggedin=True)
    @action(allowed=['post'], require_loggedin=True)
    def capture(self, request, **kwargs):
        '''
        /api/v1/payment/1/capture/?username=admin&api_key=53bf26edd8fc0252db480c746cfe995e1facb928
        {
            'correlationid' : <correlation id>
        }
        '''
        pk = kwargs['pk']
        payment = OrderPayment.objects.get(pk=pk)
        processor = self.shoputil.get_processor_by_payment(payment)
        return processor.process_order_confirmed(request, payment.order)

    @action(allowed=['post'], static=True, require_loggedin=True)
    def authorize(self, request, **kwargs):
        '''
        authorize future payments
        '''
        user = request.user
        body = json.loads(request.body)
        authorization = body.get('authorization')
        auth_code = authorization['response']['code']
        method = body['method']
        # start processing
        try:
            processor = self.shoputil.get_payment_processor(method)
        except:
            raise BadRequest('invalid payment method %s' % method)
        success, msg = processor.process_future_authorization(user, auth_code)
        if success:
            return JsonResponse({"status": 'success', "msg": msg}, status=201)
        return JsonResponse({"status": 'fail', "msg": msg}, status=400)
        
    @property
    def shoputil(self):
        return ShopUtil()
    
    @property
    def shop(self):
        return self.shoputil
    
    class Meta:
        queryset = OrderPayment.objects.all()
        resource_name = 'payment'
        authorization = DjangoAuthorization()
        authentication = ApiKeyAuthentication()
        excludes = ['authorized', 'data',]
        always_return_data = True