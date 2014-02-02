# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "github_webhooks.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
