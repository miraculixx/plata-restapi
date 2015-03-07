import json
from django.http import HttpResponse
import paypalrestsdk
from conf.settings import PAYPAL_RESTPAYMENT


api = paypalrestsdk.configure({
    "mode": PAYPAL_RESTPAYMENT.get('mode'),
    "client_id": PAYPAL_RESTPAYMENT.get('client_id'),
    "client_secret": PAYPAL_RESTPAYMENT.get('client_secret')
})

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

class BucketObject(object):
    """
    Container to keep data that doesn't conform to any orm model, but has to be returned
    by some resources.
    """

    def __init__(self, initial=None):
        self.__dict__['_data'] = {}

        if hasattr(initial, 'items'):
            self.__dict__['_data'] = initial

    def __getattr__(self, name):
        return self._data.get(name, None)

    def __setattr__(self, name, value):
        self.__dict__['_data'][name] = value

    def to_dict(self):
        return self._data


class dict2obj(object):
    """
    Convert dictionary to object
    @source http://stackoverflow.com/a/1305561/383912
    """

    def __init__(self, d):
        self.__dict__['d'] = d

    def __getattr__(self, key):
        value = self.__dict__['d'][key]
        if type(value) == type({}):
            return dict2obj(value)

        return value
    
    
class ShopUtil(object):
    @property
    def shop(self):
        """
        use this to get a shop instance without interfering
        with the Django startup. If you include shop_instance
        in the top level you may end up importing too much for
        Django to chew on during module loading.
        """
        from plata import shop_instance
        return shop_instance()
    
    def get_shop_instance(self):
        return self.shop
        
    def get_payment_processor(self, method):
        """
        from plata.shop.forms:152
        """
        payment_modules = self.shop.get_payment_modules()
        module = dict((m.key, m) for m in payment_modules).get(method)
        assert module is not None, ("Payment processor for method %s "
                        "not found in %s" % (method, payment_modules))
        return module
     
    def get_processor_by_payment(self, payment):
        """
        return the payment processor for a payment
        :param payment: Plata payment instance
        """
        return self.get_payment_processor(payment.payment_module_key)
