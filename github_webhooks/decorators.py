# Copyright (c) 2015 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from django.utils.decorators import decorator_from_middleware

from github_webhooks.middleware import PayloadMiddleware
from github_webhooks.middleware import SignatureMiddleware


add_github_payload = decorator_from_middleware(PayloadMiddleware)
require_github_signature = decorator_from_middleware(SignatureMiddleware)
