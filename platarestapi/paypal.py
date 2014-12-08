from decimal import Decimal
import logging
import urllib2

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

import plata
from plata.payment.modules.base import ProcessorBase
from plata.shop.models import OrderPayment
from platarestapi.utils import *
from paypalrestsdk import Capture, ResourceNotFound

csrf_exempt_m = method_decorator(csrf_exempt)


logger = logging.getLogger('platarestapi.paypal')


class PaymentProcessor(ProcessorBase):
    key = 'paypalrestapi'
    default_name = _('Paypal')

    def process_order_confirmed(self, request, order):
        data = json.loads(request.body)
        result, message = charge_wallet(
        transaction=data.get('transactions')[0], customer_id=data.get('customer_id'),
        correlation_id=data.get('correlation_id'), intent=data.get('intent')
        )

        if not order.balance_remaining:
            return self.already_paid(order)
        logger.info('Processing order %s using Paypal' % order)
        if order.payments.first():
            payment = order.payments.first()
        else:
            payment = self.create_pending_payment(order)
        data = payment.data
        try:
            # print data.get('transactions')[0].get('related_resources')[0].get('sale').get('id')
            # pp_transaction_id = data.get('transactions')[0].get('related_resources')[0].get('sale').get('id')
            # capture = Capture.find(pp_transaction_id)
            #
            #
            # amount_client = capture.amount.total
            # currency_client = capture.amount.currency
            # sale_state = capture.state
            #
            # amount_server = order.total
            # currency_server = order.currency
            #
            #
            # if (Decimal(amount_server) != Decimal(amount_client)):
            #     print amount_server
            #     print amount_client
            #     msg = 'Payment amount does not match order.'
            # elif (currency_client != currency_server):
            #     msg = 'Payment currency does not match order.'
            # elif sale_state != 'completed':
            #     msg = 'Sale not completed.'
            # else:
            #     msg = 'Payment has been completed.'
            data["capture"] = {
                 "request":  json.loads(json.dumps(request.body, ensure_ascii=False)),
                 "response": json.loads(json.dumps(str(request.body)))
          }
        except Exception, e:
            print str(e)

        payment.data = data
        payment.save()
        return JsonResponse({"payment_id": payment.id, "msg": message})
