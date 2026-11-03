"""
WSGI config for the HR Assistant project.

Set DJANGO_SETTINGS_MODULE=config.django.production in the deployment
environment. The local settings module is only the safe development default.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.django.local")

application = get_wsgi_application()
