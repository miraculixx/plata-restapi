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
        """


        """
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
            data["capture"] = {
                 "request":  json.loads(json.dumps(request.body, ensure_ascii=False)),
                 "response": json.loads(json.dumps(str(request.body)))
          }
        except Exception, e:
            print str(e)

        payment.data = data
        payment.save()
        return JsonResponse({"payment_id": payment.id, "msg": message})
