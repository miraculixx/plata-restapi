import json
from django.http import HttpResponsePermanentRedirect
from django.test import TestCase
from plata.shop.models import TaxClass, Order
from shop.models import *
from django.test.client import Client

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