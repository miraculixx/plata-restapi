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

def verify_payment(payment):
    try:
        payment_response = payment.data.get('create').get('response')
        response_type = payment_response.get('response_type', '')
        if response_type == 'payment':
            payment_id = payment_response.get('response').get('id')
            payment_server = paypalrestsdk.Payment.find(payment_id)
            data = payment.data
            data["capture"] = {
            "response": payment_server
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
            sale_state = transaction.related_resources[0].authorization.state

            if (Decimal(amount_server) != Decimal(amount_client)):
                return False, 'Payment amount does not match order.'
            elif (currency_client != currency_server):
                return False, 'Payment currency does not match order.'
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


def get_refresh_token(customer_id=None, auth_code=None):
    """Send authorization code after obtaining customer
    consent. Exchange for long living refresh token for
    creating payments in future
    """
    refresh_token = api.get_refresh_token(auth_code)
    return refresh_token



def charge_wallet(transaction, customer_id=None, correlation_id=None, intent="authorize"):
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
    payment = paypalrestsdk.Payment({
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

    refresh_token = get_refresh_token(customer_id)

    if not refresh_token:
        return False, "Customer has not granted consent as no refresh token has been found for customer. Authorization code needed to get new refresh token."

    if payment.create(refresh_token, correlation_id):
        print("Payment %s created successfully" % (payment.id))
        if payment['intent'] == "authorize":
            authorization_id = payment['transactions'][0]['related_resources'][0]['authorization']['id']
            print(
                "Payment %s authorized. Authorization id is %s" % (
                    payment.id, authorization_id
                )
            )
        return True, "Charged customer " + customer_id + " " + transaction["amount"]["total"]
    else:
        return False, "Error while creating payment:" + str(payment.error)


def create_payment():
    pp = paypalrestsdk.Payment({
        "intent": "authorize",

        # ###Payer
        # A resource representing a Payer that funds a payment
        # Use the List of `FundingInstrument` and the Payment Method
        # as 'credit_card'
        "payer": {
            "payment_method": "credit_card",

            # ###FundingInstrument
            # A resource representing a Payeer's funding instrument.
            # Use a Payer ID (A unique identifier of the payer generated
            # and provided by the facilitator. This is required when
            # creating or using a tokenized funding instrument)
            # and the `CreditCardDetails`
            "funding_instruments": [{

                                        # ###CreditCard
                                        # A resource representing a credit card that can be
                                        # used to fund a payment.
                                        "credit_card": {
                                            "type": "visa",
                                            "number": "4417119669820331",
                                            "expire_month": "11",
                                            "expire_year": "2018",
                                            "cvv2": "874",
                                            "first_name": "Joe",
                                            "last_name": "Shopper",

                                            # ###Address
                                            # Base Address used as shipping or billing
                                            # address in a payment. [Optional]
                                            "billing_address": {
                                                "line1": "52 N Main ST",
                                                "city": "Johnstown",
                                                "state": "OH",
                                                "postal_code": "43210",
                                                "country_code": "US"}}}]},
        # ###Transaction
        # A transaction defines the contract of a
        # payment - what is the payment for and who
        # is fulfilling it.
        "transactions": [{

                             # ### ItemList
                             "item_list": {
                                 "items": [{
                                               "name": "item",
                                               "sku": "item",
                                               "price": "1.00",
                                               "currency": "USD",
                                               "quantity": 1}]},

                             # ###Amount
                             # Let's you specify a payment amount.
                             "amount": {
                                 "total": "1.00",
                                 "currency": "USD"},
                             "description": "This is the payment transaction description."}]})
    if pp.create():
        return pp
    return None