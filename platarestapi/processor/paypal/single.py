import logging

from django.utils.translation import ugettext as _
from plata.payment.modules.base import ProcessorBase
from plata.shop.models import OrderPayment

from platarestapi.processor.paypal.mixin import PaypalProcessorMixin, \
    PaypalConstants
from platarestapi.utils import JsonResponse


logger = logging.getLogger(__name__)

class SinglePaymentProcessor(PaypalProcessorMixin, ProcessorBase):
    """
    Single payment processor
    
    Processes Paypal's single payment. A single payment means the client
    has authorized & executed the payment. We receive an authorization code 
    that we check back with Paypal. If the authorization is confirmed by
    Paypal, the SinglePaymentProcessor updates Plata's payment status to
    OrderPayment.PROCESSED, otherwise leaves it unchanged.
    """
    key = 'paypal-rest-single'
    default_name = _('Paypal Rest Single')
    
    def get_or_create_pending_payment(self, order, order_id=None, 
                                      authorization=None):
        """
        retrieve order, or create pending
        
        Retrieve the first payment known for this order, or create a pending
        payment. Stores the order_id and authorization data.
        
        :param order:  Plata order instance
        :param order_id:  Paypal provider order id
        :param authorization: Paypal provider authorization 
        """
        payment = order.payments.first() or self.create_pending_payment(order)
        if order_id or authorization:
            payment.data['capture'] = {'order_id' : order_id or '', 
                                       'authorization' : authorization or {}, 
                                       'method' : self.key}
            payment.save()
        return payment

    def process_order_confirmed(self, request, order, order_id, authorization):
        """
        process a confirmed order
        
        called by the API to confirm a payment. Since this is a single
        payment we expect the payment to be approved according to 
        https://developer.paypal.com/webapps/developer/docs/integration/mobile/verify-mobile-payment/
        
        :param request: request object 
        :param order:  Plata order instance
        :param order_id:  Paypal provider order id
        :param authorization: Paypal provider authorization
        """
        # get Plata payment
        payment = self.get_or_create_pending_payment(order, order_id, 
                                                     authorization)
        # assert we have the necessary data
        msg = "invalid payment data %s" % payment.data
        try:
            create_data = payment.data.get('capture').get('authorization')
            response_type = create_data.get('response_type')
        except Exception as e:
            response_type = None
        # process payment (response_type == 'payment'
        logger.info('Processing order %s using Paypal' % order)
        if response_type != 'payment':
            return JsonResponse({'status' : 'failed', 'msg' : msg })
        # -- ask paypal if the payment is known and approved
        approved, message = self.verify_payment(payment, PaypalConstants.APPROVED, 
                        PaypalConstants.COMPLETED, user=request.user)
        # -- since this is approved by PayPal, set Plata payment status
        if not approved:
            msg = "payment was not approved" % payment.data
            return JsonResponse({'status' : 'failed', 'msg' : msg })
        if approved:
            payment.status = OrderPayment.PROCESSED
            payment.transaction_id = order_id
            payment.payment_method = payment.payment_module
            payment.save()
            order = order.reload()
        return JsonResponse({"payment_id": payment.id, "msg": message})