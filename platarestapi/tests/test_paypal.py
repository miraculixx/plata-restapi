from decimal import Decimal
import urlparse

from django.conf import settings
from django.contrib.auth.models import User
from django.test.client import Client
import paypalrestsdk
from plata.shop.models import TaxClass, Order, OrderPayment
from pyvirtualdisplay import display
from pyvirtualdisplay.display import Display
from tastypie.test import ResourceTestCase

from platarestapi.utils import api
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
        if pk is None and action is None:
            return '/api/v1/shop/%s/' % resource
        if pk and action is None:
            return '/api/v1/shop/%s/%s/' % (resource, pk)
        if pk is None and action:
            return '/api/v1/shop/%s/%s/' % (resource, action)
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
        
    def test_authorize_future_payment(self):
        data = {
            'authorization' : self.ppsdk_future_authorization,
            'method' : 'paypal-rest-future',
        } 
        resp = self.api_client.post(self.url('payment', action='authorize'),
                                    format='json',
                                    data=data, 
                                    authentication=self.credentials())
        print resp
        self.assertHttpCreated(resp)
        rdata = self.deserialize(resp, resp)
        print rdata
        
    def test_paypal_create_payment(self):
        # https://devtools-paypal.com/guide/pay_paypal/python?interactive=ON&env=sandbox
        pp = paypalrestsdk
        access_token = api.get_access_token()
        pp_payment = pp.Payment({
                        'intent' : 'sale', 
                        'payer' : {
                            'payment_method' : 'paypal',
                        },
                        'transactions' : [{
                            'amount' : {
                                'total' : str(12),
                                'currency' : 'USD',
                            },
                            'description' : 'a paypal test payment'
                        }],
                        'redirect_urls' : {
                            'return_url' : 'http://localhost/success',
                            'cancel_url' : 'http://localhost/cancel',
                        },
                    })
        self.assertTrue(pp_payment.create(), 'could not create paypal payment %s' % pp_payment.error)
        # release it. this is akin to the client sdk making a payment
        approval_url = self.get_url_from_payment(pp_payment, 'approval_url')
        authorization = self.pp_confirm_payment_interactive(approval_url)
        self.pp_execute_payment(authorization)
        # now record the payment in the api
        data = {}
        payment = self.create_payment(self.order, 'paypal-rest-single', 
                                      data=data)
         
                
    def pp_confirm_payment_interactive(self, approval_url):
        """
        using the Firefox webdriver, confirm the payment
        
        this returns an authorization of the form 
        
        {
         u'paymentId': [u'PAY-5AC58518MT5069320KT7NHLA'], 
         u'token': [u'EC-0FS41045Y0067720N'], 
         u'PayerID': [u'2W6SK2DEBB5TU']
        }
        
        for headless mode, make sure you have installed
           apt-get install xvfb
           pip install pyvirtualdisplay
           
        http://scraping.pro/use-headless-firefox-scraping-linux/
        """
        from selenium import webdriver
        from selenium.webdriver.common.keys import Keys
        display = Display(visible=0, size=(800,600))
        display.start()
        br = webdriver.Firefox()
        br.get(approval_url)
        e = br.find_element_by_id('loadLogin')
        e.click()
        e = br.find_element_by_id('login_email')
        e.send_keys(settings.PAYPAL_TESTUSER)
        e = br.find_element_by_id('login_password')
        e.send_keys(settings.PAYPAL_TESTUSER_PASSWORD)
        e = br.find_element_by_id('submitLogin')
        e.click()
        e = br.find_element_by_id('continue')
        e.click()
        # response url is of the form
        # http://<return_url>?paymentId=PAY-6RV70583SB702805EKEYSZ6Y&token=EC-60U79048BN7719609&PayerID=7E7MGXCWTTKK2
        # see https://developer.paypal.com/docs/integration/web/accept-paypal-payment/#get-payment-approval
        response_url = br.current_url
        parts = urlparse.urlparse(response_url)
        authorization = urlparse.parse_qs(parts.query)
        br.get_screenshot_as_file('payment.png')
        br.quit()
        display.stop()
        return authorization
    
    def pp_execute_payment(self, authorization):
        pp = paypalrestsdk
        payment = pp.Payment.find(authorization['paymentId'])
        resp = payment.execute({'payer_id' : authorization['PayerID']})
        print resp
        
    def get_url_from_payment(self, pp_payment, rel):
        """
        from a Payment response, retrieve the URL rel
        """
        links = filter(lambda l : l['rel'] == rel, pp_payment['links'])
        return links[0]['href']
    
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
    
    @property
    def ppsdk_future_authorization(self):
        # this is the response to authorizing future payments created
        # by the paypal mobile sdk
        data = {
            "response": {
                "code": "EM-glBRRgM-uVWT59rUvJ8-zws0gn8rhzdCCS-GKfyCXWXV2lTX3St3IMweV9m2hSoSeHh9y5Pzmkg2dUxz1n0eVt_2r3mGkms1FYfwwPwKCT4ccUOX6Sq3VhLEfKUXams3l4BQeJksT13ULGyTWDjVtyU_wR6gdkj81f5Yxw2_N"
            },
            "client": {
                "platform": "Android",
                "paypal_sdk_version": "2.7.1",
                "product_name": "PayPal-Android-SDK",
                "environment": "sandbox"
            },
            "response_type": "authorization_code"
        }
        return data 