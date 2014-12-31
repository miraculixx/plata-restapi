import json

from django.db import transaction
from django.db.utils import IntegrityError
from django.http import HttpResponsePermanentRedirect
from django.test import TestCase
from django.test.client import Client
from plata.shop.models import TaxClass, Order, OrderPayment
from tastypie.authentication import ApiKeyAuthentication
from tastypie.test import ResourceTestCase

from shop.models import *


class OrderPaymentTestCase(TestCase):
    def setUp(self):
        product = Product(name='Test', slug='test')
        product.save()
        tax = TaxClass(name='VAT', rate=10.00)
        tax.save()
        price = ProductPrice(product=product, currency='USD', _unit_price=500.00, tax_included=1, tax_class=tax)
        price.save()
        order = Order(user_id=1)
        order.save()
        order.payments.create(
            currency=order.currency,
            amount=order.balance_remaining,
            payment_module_key='',
            payment_module='',
        )

    def test_create_payment(self):
        c = Client()
        response = c.post('/api/v1/payment/', {'order_id': 1}, content_type="application/json")
        print response
        self.assertIsNotNone(isinstance(response, HttpResponsePermanentRedirect))

    def test_update_payment(self):
        c = Client()
        response = c.put('/api/v1/payment/1/', data={}, content_type="application/json")
        print response
        self.assertEqual(response.get('status'), "success")

    def test_verify_payment(self):
        c = Client()
        order = Order(user_id=1)
        order.save()
        order.payments.create(
            currency=order.currency,
            amount=order.balance_remaining,
            payment_module_key='',
            payment_module='',
        )
        response = c.get('/api/v1/payment/1/verify/', content_type="application/json")
        print response
        self.assertEqual(response.get('status'), "success")
        

class PlataRestAPITests(ResourceTestCase):
    def setUp(self):
        super(PlataRestAPITests, self).setUp()
        # setup a user with an API key
        from tastypie.models import ApiKey
        self.user = User.objects.create_user("test", "test@example.com", "test")
        ApiKey.objects.get_or_create(user=self.user)
            
    def tearDown(self):
        super(PlataRestAPITests, self).tearDown()
        
    def uri(self, pk=None, action=None):
        if pk and action:
            return '/api/v1/payment/%s/%s/' % (pk, action)
        elif pk:
            return '/api/v1/payment/%s/' % pk
        else:
            return '/api/v1/payment/' 
        
    def get_credentials(self):
        return self.create_apikey(self.user.username, self.user.api_key.key)
        
    def test_create_payment(self):
        order = self.createOrder()
        data = {
          'order_id' : order.pk        
        }
        # create payment, verify it gets created 
        response = self.api_client.post(self.uri(), data=data, format='json',
                                        authentication=self.get_credentials())
        self.assertHttpCreated(response)
        self.assertIn(self.uri(1), response['Location'])
        
    def test_create_payment_verify_fail(self):
        """ 
        same as test_create_payment, but this fails if the order
        is not in "failed" state after first verification
        """
        order = self.createOrder()
        data = {
          'order_id' : order.pk        
        }
        # create payment, verify it gets created 
        response = self.api_client.post(self.uri(), data=data, format='json',
                                        authentication=self.get_credentials())
        self.assertHttpCreated(response)
        self.assertIn(self.uri(1), response['Location'])
        # verify it is not ok yet
        OrderPayment.objects.get(order=order)
        response = self.api_client.get(self.uri(order.pk, 'verify'),
                                      authentication=self.get_credentials())
        self.assertHttpOK(response)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'failed')
        
    def test_verify_payment(self):
        order = self.createOrder()
        payment = self.createPayment(order)
        raise NotImplementedError
        
        
    def test_capture_payment(self):
        order = self.createOrder()
        payment = self.createPayment(order)
        # capture the payment
        response = self.api_client.put(self.uri(payment.pk, 'capture'),
                                       authentication=self.get_credentials())
        data = json.loads(response.content)
        self.assertEqual()
        
    def createPayment(self, order):    
        payment = order.payments.create(
            currency=order.currency,
            amount=order.balance_remaining,
            payment_module_key='',
            payment_module='',
        )
        return payment
        
    def createOrder(self):
        product = Product(name='Test', slug='test')
        product.save()
        tax = TaxClass(name='VAT', rate=10.00)
        tax.save()
        price = ProductPrice(product=product, currency='USD', _unit_price=500.00, tax_included=1, tax_class=tax)
        price.save()
        order = Order(user_id=1, currency='USD')
        order.save()
        order.modify_item(product, absolute=1)
        return order
        
    