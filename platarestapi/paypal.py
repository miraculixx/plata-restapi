from decimal import Decimal
import logging
import urllib2

from django.conf import settings
from django.contrib.auth.models import User
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

class SinglePaymentProcessor(ProcessorBase):
    key = 'paypal-rest-single'
    default_name = _('Paypal Rest Single')

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
        response_type = 'authorization_code'
        try:
            response_type = payment.data.get('create').get('response').get('response_type')
        except:
            pass
        if response_type == 'payment':
            payment_id=payment.data.get('create').get('response').get('response').get('authorization_id')
            print payment_id
            authorization = Authorization.find(payment_id)
            print authorization
            if authorization.state == 'captured':
                return JsonResponse({"payment_id": payment.id, "msg": "This payment was captured"})
            capture = authorization.capture({
                "amount": {
                    "currency": payment.currency,
                    "total": str(payment.amount)},
                "is_final_capture": True})
            print capture
            result, message = capture, capture.success()

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


class FuturePaymentProcessor(ProcessorBase):
    key = 'paypal-rest-future'
    default_name = _('Paypal Rest Future')

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

        correlation_id = request.GET.get('correlation_id', '')

        user = request.user
        result, message = charge_wallet(payment,
                                        transaction=transaction,
                                        correlation_id=correlation_id, intent='sale', user=user
        )
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
        response_type = 'authorization_code'
        try:
            response_type = payment.data.get('create').get('response').get('response_type')
        except:
            pass
        if response_type == 'payment':
            payment_id=payment.data.get('create').get('response').get('response').get('authorization_id')
            print payment_id
            authorization = Authorization.find(payment_id)
            print authorization
            if authorization.state == 'captured':
                return JsonResponse({"payment_id": payment.id, "msg": "This payment was captured"})
            capture = authorization.capture({
                "amount": {
                    "currency": payment.currency,
                    "total": str(payment.amount)},
                "is_final_capture": True})
            print capture
            result, message = capture, capture.success()
        else:
            user = request.user
            result, message = charge_wallet(payment,
                                            transaction=transaction,
                                            correlation_id=order.email, intent='sale', user=user
            )
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
