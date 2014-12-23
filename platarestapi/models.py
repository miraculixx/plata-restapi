from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

class PaymentAuthorization(models.Model):
	is_active = models.BooleanField(_('is active'), default=True)
	user = models.ForeignKey(User, verbose_name=_('User'), related_name='payment_authorizations')
	access_token = models.CharField(default='', max_length=255, blank=True, null=True)
	refresh_token = models.CharField(default='', max_length=255, blank=True, null=True)
	created = models.DateTimeField(_('Created'), auto_now_add=True,
								   editable=False)
	modified = models.DateTimeField(_('Modified'), auto_now=True, editable=False)
	class Meta:
		db_table = u'payment_authorizations'
		verbose_name_plural = "Payment Authorizations"
