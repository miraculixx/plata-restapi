import logging

from django.utils.translation import ugettext as _
from plata.payment.modules.base import ProcessorBase

from platarestapi.processor.paypal.mixin import PaypalProcessorMixin
from platarestapi.utils import JsonResponse


logger = logging.getLogger(__name__)

class FuturePaymentProcessor(PaypalProcessorMixin, ProcessorBase):
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
        result, message = self.charge_wallet(payment,
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