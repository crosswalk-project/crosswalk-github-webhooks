# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

INSTALLED_APPS = (
    'github_webhooks',
    'trybot_control',
    'jira_updater'
)

MIDDLEWARE_CLASSES = (
)

ROOT_URLCONF = 'github_webhooks.urls'

SECRET_KEY = 'w#k&%d&$dckugfwqx-i3n@6cx_)^ea^kmpscbl+byq(#pldbb-'

TIME_ZONE = 'UTC'

USE_I18N = False

WSGI_APPLICATION = 'github_webhooks.wsgi.application'

# Get internal settings (passwords, access tokens etc from another file that is
# not part of the repository).
from internal_settings import *
