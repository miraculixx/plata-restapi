from decimal import Decimal
import logging
import urllib2

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from paypalrestsdk import Authorization
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
        if order.payments.first():
            payment = order.payments.first()
        else:
            payment = self.create_pending_payment(order)
        transaction = {
            "amount": {
                "total": str(payment.amount),
                "currency": payment.currency
            },
            "description": payment.notes
        }

        response_type = payment.data.get('create').get('response').get('response_type')
        if response_type == 'payment':
            authorization = Authorization.find(
                payment.data.get('create').get('response').get('response').get('authorization_id'))
            if authorization.state == 'captured':
                return JsonResponse({"payment_id": payment.id, "msg": "This payment was captured"})
            capture = authorization.capture({
                "amount": {
                    "currency": payment.currency,
                    "total": str(payment.amount)},
                "is_final_capture": True})

            result, message = capture, capture.success()
        else:
            result, message = charge_wallet(payment,
                                            transaction=transaction,
                                            auth_code=payment.data.get('create').get('response').get('response').get(
                                                'code'),
                                            correlation_id=order.email, intent='sale'
            )
        print result, message
        if not order.balance_remaining:
            return self.already_paid(order)
        logger.info('Processing order %s using Paypal' % order)

        data = payment.data
        try:
            data["capture"] = {
                "response": str(result)
            }
        except Exception, e:
            print 'error', str(e)

        payment.data = data
        payment.save()
        return JsonResponse({"payment_id": payment.id, "msg": message})
