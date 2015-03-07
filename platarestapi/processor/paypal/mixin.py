'''
Created on Mar 3, 2015

@author: patrick
'''
from decimal import Decimal
import json

import paypalrestsdk

from platarestapi.models import PaymentAuthorization

class PaypalConstants:
    # states
    APPROVED='approved'
    CAPTURED='captured'
    COMPLETED='completed'


class PaypalProcessorMixin(object):
    """
    Mixin to Plata payment ProcessorBase 
    
    Methods to interact with Paypal
    """
    def verify_payment(self, payment, expected_payment_state, 
                       expected_tx_state, user=None):
        '''
        verify that a payment has actually been processed. will lookup
        the payment at Paypal and verify that
        
        1. pp payment.state == 'approved'
        2. pp sale state == 'captured'
        3. plata and pp payment currency + amounts match
        
        payment.data['verify'] will contain the pp response. 
        
        :param payment: Plata payment
        :param user: Django user
        :param expected_payment_state: expected state, see PaypalConstants
        :param expected_tx_state: expected state, see PaypalConstants
        :return: (result, message), where result is True if all of above 
        conditions satisfied, False otherwise. message is a text message
        for debugging purpose 
        '''
        # get payment from paypal
        try:
            # -- get the paypal data
            payment_response = payment.data.get('capture').get('authorization').get('response')
            payment_id = payment_response['id']
        except:
            raise AssertionError, 'invalid payment data %s' % payment.data
        try:
            # -- check response is valid 
            # :see: ./responses/payment_find.json
            pp_payment = paypalrestsdk.Payment.find(payment_id)
            data = payment.data
            data["verify"] = {
                "response": json.loads(json.dumps(str(pp_payment)))
            }
        except paypalrestsdk.ResourceNotFound:
            return False, 'Paypal payment not Found %s' % payment_id
        except:
            raise AssertionError, 'Invalid response from paypal ' % pp_payment 
        else:
            payment.save()
        # verify the payment status
        # according to https://developer.paypal.com/webapps/developer/docs/integration/mobile/verify-mobile-payment/
        if pp_payment.state != expected_payment_state:
            return False, 'Payment state is %s (expected %s)' % (pp_payment.state, expected_payment_state)
        amount_client = payment.amount
        currency_client = payment.currency
        # Get most recent transaction
        transaction = pp_payment.transactions[0]
        amount_server = transaction.amount.total
        currency_server = transaction.amount.currency
        # always check amount / currency
        if (Decimal(amount_server) != Decimal(amount_client)):
            return False, 'Payment amount does not match order.'
        elif (currency_client != currency_server):
            return False, 'Payment currency does not match order.'
        # check authorization or sale state
        if transaction.related_resources[0].authorization:
            sale_state = transaction.related_resources[0].authorization.state
        else:
            sale_state = transaction.related_resources[0].sale.state
        return sale_state == expected_tx_state, ('Payment.tx state is %s'
                                              ' (expected %s)' % (sale_state, 
                                                            expected_tx_state))
        
    def get_refresh_token(self, user=None):
        """Send authorization code after obtaining customer
        consent. Exchange for long living refresh token for
        creating payments in future
        """
        refresh_token = None
        if PaymentAuthorization.objects.filter(user=user):
            payment_authorization = PaymentAuthorization.objects.filter(user=user).first()
            refresh_token = payment_authorization.refresh_token
        return refresh_token
    
    
    def charge_wallet(self, payment, transaction, correlation_id=None, intent="authorize", user=None):
        """Charge a customer who formerly consented to future payments
        from paypal wallet.
        {
           'update_time':   u'2014-12-19T14:26:49   Z',
           'payer':{
              'payment_method':u'paypal',
              'status':u'VERIFIED',
              'payer_info':{
                 'first_name':u'SandboxTest',
                 'last_name':u'Account',
                 'email':u'huy@mac.com',
                 'payer_id':u'H7ZBSNRZ5C7DL'
              }
           },
           'links':[
              {
                 'href':         u'https://api.sandbox.paypal.com/v1/payments/payment/PAY-0BV260076T944302DKSKDLJY',
                 'method':u'GET',
                 'rel':u'self'
              }
           ],
           'transactions':[
              {
                 'amount':{
                    'currency':u'USD',
                    'total':u'100.00',
                    'details':{
                       'subtotal':u'100.00'
                    }
                 },
                 'related_resources':[
                    {
                       'authorization':{
                          'valid_until':                  u'2015-01-17T14:26:47                  Z',
                          'protection_eligibility':u'INELIGIBLE',
                          'update_time':                  u'2014-12-19T14:26:49                  Z',
                          'links':[
                             {
                                'href':                        u'https://api.sandbox.paypal.com/v1/payments/authorization/1U302828U8702213S',
                                'method':u'GET',
                                'rel':u'self'
                             },
                             {
                                'href':                        u'https://api.sandbox.paypal.com/v1/payments/authorization/1U302828U8702213S/capture',
                                'method':u'POST',
                                'rel':u'capture'
                             },
                             {
                                'href':                        u'https://api.sandbox.paypal.com/v1/payments/authorization/1U302828U8702213S/void',
                                'method':u'POST',
                                'rel':u'void'
                             },
                             {
                                'href':                        u'https://api.sandbox.paypal.com/v1/payments/authorization/1U302828U8702213S/reauthorize',
                                'method':u'POST',
                                'rel':u'reauthorize'
                             },
                             {
                                'href':                        u'https://api.sandbox.paypal.com/v1/payments/payment/PAY-0BV260076T944302DKSKDLJY',
                                'method':u'GET',
                                'rel':u'parent_payment'
                             }
                          ],
                          'amount':{
                             'currency':u'USD',
                             'total':u'100.00',
                             'details':{
                                'subtotal':u'100.00'
                             }
                          },
                          'id':u'1U302828U8702213S',
                          'state':u'authorized',
                          'create_time':                  u'2014-12-19T14:26:47                  Z',
                          'payment_mode':u'INSTANT_TRANSFER',
                          'parent_payment':u'PAY-0BV260076T944302DKSKDLJY'
                       }
                    }
                 ]
              }
           ],
           'state':u'approved',
           'create_time':   u'2014-12-19T14:26:47   Z',
           'intent':u'authorize',
           'id':u'PAY-0BV260076T944302DKSKDLJY'
        }
        """
        pp_payment = paypalrestsdk.Payment({
            "intent": intent,
            "payer": {
                "payment_method": "paypal"
            },
            "transactions": [{
                                 "amount": {
                                     "total": transaction["amount"]["total"],
                                     "currency": transaction["amount"]["currency"]
                                 },
                                 "description": transaction["description"]
                             }]})
        refresh_token = self.get_refresh_token(user)
        if not refresh_token:
            return False, "Customer has not granted consent as no refresh token has been found for customer. Authorization code needed to get new refresh token."
    
        if pp_payment.create(refresh_token, correlation_id):
            print("Payment %s created successfully" % (pp_payment.id))
            if pp_payment['intent'] == "authorize":
                authorization_id = pp_payment['transactions'][0]['related_resources'][0]['authorization']['id']
                print(
                    "Payment %s authorized. Authorization id is %s" % (
                        pp_payment.id, authorization_id
                    )
                )
            return pp_payment, "Charged customer " + user.username + " " + transaction["amount"]["total"]
        else:
            return False, "Error while creating payment:" + str(payment.error)
