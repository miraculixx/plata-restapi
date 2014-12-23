import json
from decimal import Decimal
from django.http import HttpResponse
import paypalrestsdk
from conf.settings import PAYPAL_RESTPAYMENT
import logging


class JsonResponse(HttpResponse):
    """
        JSON response
    """

    def __init__(self, content, content_type='application/json', status=None):
        super(JsonResponse, self).__init__(
            content=json.dumps(content),
            content_type=content_type,
            status=status
        )


logging.basicConfig(level=logging.DEBUG)

api = paypalrestsdk.configure({
    "mode": PAYPAL_RESTPAYMENT.get('mode'),
    "client_id": PAYPAL_RESTPAYMENT.get('client_id'),
    "client_secret": PAYPAL_RESTPAYMENT.get('client_secret')
})


def verify_payment(payment, user=None):
    try:
        payment_response = payment.data.get('create').get('response')
        response_type = payment_response.get('response_type', '')
        print response_type
        if response_type == 'payment':
            payment_id = payment_response.get('response').get('id')
            payment_server = paypalrestsdk.Payment.find(payment_id)
            data = payment.data
            data["verify"] = {
                "response": json.loads(json.dumps(str(payment_server)))
            }
            payment.save()
            if payment_server.state != 'approved':
                return False, 'Payment has not been approved yet. Status is ' + payment_server.state + '.'

            amount_client = payment.amount
            currency_client = payment.currency

            # Get most recent transaction
            transaction = payment_server.transactions[0]
            amount_server = transaction.amount.total
            currency_server = transaction.amount.currency
            if transaction.related_resources[0].authorization:
                sale_state = transaction.related_resources[0].authorization.state
            else:
                sale_state = transaction.related_resources[0].sale.state
            print sale_state
            if (Decimal(amount_server) != Decimal(amount_client)):
                return False, 'Payment amount does not match order.'
            elif (currency_client != currency_server):
                return False, 'Payment currency does not match order.'
            elif sale_state == 'captured':
                return True, 'Payment has been captured.'
            elif sale_state != 'completed':
                return False, 'Sale not completed.'
            else:
                return True, 'Payment has been authorized.'
        elif response_type == 'authorization_code':
            return True, 'Received consent'

        else:
            return False, 'Invalid response type'

    except paypalrestsdk.ResourceNotFound:
        return False, 'Payment Not Found'


def get_refresh_token(auth_code=None, user=None):
    """Send authorization code after obtaining customer
    consent. Exchange for long living refresh token for
    creating payments in future
    """
    if PaymentAuthorization.objects.filter(user=user):
        paymentauthorization = PaymentAuthorization.objects.filter(user=user).first()
        refresh_token = paymentauthorization.refresh_token
    else:    
        refresh_token = api.get_refresh_token(auth_code)
        paymentauthorization = PaymentAuthorization(user=user)
        paymentauthorization.access_token = auth_code
        paymentauthorization.refresh_token = refresh_token
        paymentauthorization.save()

    return refresh_token


def charge_wallet(payment, transaction, auth_code=None, correlation_id=None, intent="authorize", user=None):
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
    try:
        refresh_token = get_refresh_token(auth_code, user)
        payment.data['refresh_token'] = refresh_token
        payment.save()
        print refresh_token
    except Exception, e:
        refresh_token = payment.data.get('refresh_token', '')

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
        return pp_payment, "Charged customer " + auth_code + " " + transaction["amount"]["total"]
    else:
        return False, "Error while creating payment:" + str(payment.error)
