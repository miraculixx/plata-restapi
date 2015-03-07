from decimal import Decimal

from django.contrib.auth.models import User
from django.test.client import Client
import paypalrestsdk
from plata.shop.models import TaxClass, Order, OrderPayment
from tastypie.test import ResourceTestCase

from shop.models import Product, ProductPrice


class OrderPaymentPaypalTests(ResourceTestCase):
    def setUp(self):
        super(OrderPaymentPaypalTests, self).setUp()
        from plata import shop_instance
        self.shop = shop_instance()
        self.password = 'test'
        self.username = 'pass'
        self.user = User.objects.create_user(self.username, 
                                             password=self.password)
        self.setup_shopdata()
        
    def url(self, resource, pk=None, action=None):
        if pk is None:
            return '/api/v1/shop/%s/' % resource
        if action is None:
            return '/api/v1/shop/%s/%s/' % (resource, pk)
        else:
            return '/api/v1/shop/%s/%s/%s/' % (resource, pk, action)
        
    def credentials(self):
        return self.create_apikey(self.user.username, self.user.api_key.key)

    def test_create_invalid_payment(self):
        """
        attempt to create an invalid payment (invalid payment method)
        """
        order = self.order
        data = {
            'method' : 'paypal-rest-nonexistent',
            'order_id' : order.pk,
            'authorization' : self.ppsdk_single_payment
        } 
        resp = self.api_client.post(self.url('payment'), data=data, 
                                   format='json', 
                                   authentication=self.credentials())
        self.assertHttpBadRequest(resp)
        
    def test_create_single_payment(self):
        """
        create a single payment with valid data. for this to succeed
        .ppsdk_single_payment() must return a valid and existing paypal
        payment with state approved (intent = sale)
        """
        order = self.order
        data = {
            'method' : 'paypal-rest-single',
            'order_id' : order.pk,
            'authorization' : self.ppsdk_single_payment
        } 
        resp = self.api_client.post(self.url('payment'), data=data, 
                                   format='json', 
                                   authentication=self.credentials())
        self.assertHttpCreated(resp)
        rdata = self.deserialize(resp)
        self.assertEqual(Decimal(rdata['amount']), order.subtotal)
        self.assertEqual(rdata['currency'], order.currency)
        self.assertEqual(rdata['payment_module_key'], data['method'])
        self.assertNotIn('authorization', rdata)
        self.assertNotIn('data', rdata)
        self.assertEqual(int(rdata['status']), OrderPayment.PROCESSED)
        
    def test_create_pending_payment(self):
        """
        test creating a pending payment, i.e. don't provide pp authorization
        data, then update in second step. result shall be the same as
        in test_create_single_payment
        """
        order = self.order
        data = {
            'method' : 'paypal-rest-single',
            'order_id' : order.pk,
            'authorization' : None
        } 
        resp = self.api_client.post(self.url('payment'), data=data, 
                                   format='json', 
                                   authentication=self.credentials())
        self.assertHttpCreated(resp)
        rdata = self.deserialize(resp)
        self.assertEqual(Decimal(rdata['amount']), order.subtotal)
        self.assertEqual(rdata['currency'], order.currency)
        self.assertEqual(rdata['payment_module_key'], data['method'])
        self.assertNotIn('authorization', rdata)
        self.assertNotIn('data', rdata)
        self.assertEqual(int(rdata['status']), OrderPayment.PENDING)
        # now update with valid authorization
        data['authorization'] = self.ppsdk_single_payment
        resp = self.api_client.put(self.url('payment', rdata['id']), data=data, 
                                   format='json', 
                                   authentication=self.credentials())
    
        self.assertHttpOK(resp)
        rdata = self.deserialize(resp)
        pk = rdata['id']
        payment = OrderPayment.objects.get(pk=pk)
        self.assertEqual(Decimal(rdata['amount']), order.subtotal)
        self.assertEqual(rdata['currency'], order.currency)
        self.assertEqual(rdata['payment_module_key'], data['method'])
        self.assertNotIn('authorization', rdata)
        self.assertNotIn('data', rdata)
        self.assertEqual(int(rdata['status']), OrderPayment.PROCESSED)
        self.assertEqual(payment.status, OrderPayment.PROCESSED)
        
    def test_verify_single_payment(self):
        data = { 'capture' : { 
                    'authorization' : self.ppsdk_single_payment 
                  } 
        }
        payment = self.create_payment(self.order, 'paypal-rest-single', 
                                      data=data)
        resp = self.api_client.get(self.url('payment', payment.pk, 
                                            action='verify'), 
                                   format='json', 
                                   authentication=self.credentials())
        rdata = self.deserialize(resp)
        self.assertEqual('success', rdata['status'])
        
    def test_verify_invalid_payment(self):
        data = { 'capture' : { 
                    'authorization' : None 
                  } 
        }
        payment = self.create_payment(self.order, 'paypal-rest-single', 
                                      data=data)
        resp = self.api_client.get(self.url('payment', payment.pk, 
                                            action='verify'), 
                                   format='json', 
                                   authentication=self.credentials())
        rdata = self.deserialize(resp)
        self.assertEqual('failed', rdata['status'])
        
    def paypal_create_payment(self):
        # this fails with INTERNAL SERVER ERROR
        pp = paypalrestsdk
        pp_payment = pp.Payment({
                        'intent' : 'sale', 
                        'payer' : {
                            'payment_method' : 'paypal',
                        },
                        'redirect_urls' : {
                            'return_url' : 'http://localhost/success',
                            'cancel_url' : 'http://localhost/cancel',
                        }
                    })
        self.assertTrue(pp_payment.create(), 'could not create paypal payment %s' % pp_payment.error)
        print pp_payment
        
    def setup_shopdata(self):
        product = Product(name='Test', slug='test')
        product.save()
        tax = TaxClass(name='VAT', rate=10.00)
        tax.save()
        price = ProductPrice(product=product, currency='USD', 
                             _unit_price=100.00, tax_included=1, tax_class=tax)
        price.save()
        order = Order.objects.create(user_id=1, currency='USD')
        order.modify_item(product, relative=1)
        self.order = order
        
    def create_payment(self, order, method, data=None):
        data = data or {'capture' : {
                        'authorization' : {
                            'response' : ''
            } 
          }
        } 
        return order.payments.create(
            currency=order.currency,
            amount=order.balance_remaining,
            payment_module_key=method,
            payment_module=method,
            data = data 
        )
        
    @property
    def ppsdk_single_payment(self):
        # this is the response to a single payment created by the client. 
        # make sure you have run this from the client
        data = {
            "response": {
                "state": "approved",
                "id": "PAY-8SC74951M4081314TKT5IRTQ",
                "create_time": "2015-03-07T05:12:46Z",
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
        return data
        