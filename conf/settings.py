"""
Django settings for platashop project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from django.utils.translation import ugettext as _

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'fwh47btv0u9%8^6el(vn+^dt0)+b5(@g7=$-qv1@*5uaqwd+qk'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS
# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'plata',
    'plata.discount',
    'plata.payment',
    'plata.product',
    'plata.shop',
    'shop',
    'platarestapi',
    'tastypie'
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'plata.context_processors.plata_context',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'conf.urls'

WSGI_APPLICATION = 'conf.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media/')
MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = '/admin_media/'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

PAYPAL_RESTPAYMENT = {
    'mode': 'sandbox',
    'client_id': 'AelEKi-x_p0SSdGOx-mQLqQpy5j0220Tr9PcWt2hqDwAsVmOvW6mp9IYSNoI3_qduYelfvY1DhPrhR8n',
    'client_secret': 'EBPq1HVQbuf82Xx9UrOdOicDWydWH5cpTCrYc8mxpbs-29VJmifLxTH0eGA6wzlkei-Wwqgsz5K9fHia'
}

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)

# PLATA settings

#PLATA_PRICE_INCLUDES_TAX = False

PLATA_SHOP_CONTACT = 'shop.Contact'


POSTFINANCE = {
    'PSPID': 'plataTEST',
    'SHA1_IN': 'plataSHA1_IN',
    'SHA1_OUT': 'plataSHA1_OUT',
    'LIVE': False,
    }

PLATA_PAYMENT_MODULE_NAMES = {
    'paypal': _('Paypal and credit cards'),
    }
PLATA_PAYMENT_MODULES = ('platarestapi.processor.paypal.SinglePaymentProcessor',
    'platarestapi.processor.paypal.FuturePaymentProcessor')    

PAYPAL = {
    'BUSINESS': 'macanhhuy@gmail.com',
    'LIVE': False,
    }

PLATA_REPORTING_ADDRESSLINE = 'Example Corp. - 3. Example Street - 1234 Example'

# TEST_RUNNER = 'options.test_utils.test_runner_with_coverage'
# COVERAGE_MODULES = ['plata']

import logging, sys
logging.basicConfig(
    filename='plata.log',
    format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
    level=logging.DEBUG,
    )

PLATA_SHOP_PRODUCT = 'shop.Product'
CURRENCIES = ('USD',)