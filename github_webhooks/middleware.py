# Copyright (c) 2015 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import hmac
import json

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.utils.crypto import constant_time_compare


class PayloadMiddleware(object):
    """
    Verifies that the HTTP POST request contains a 'payload' variable, parses
    the JSON payload and adds it to the request.
    Payloads containing a key called 'zen' are discarded, as they are pings
    sent by GitHub when a hook is added.
    """

    def process_request(self, request):
        if 'payload' not in request.POST:
            return HttpResponseNotFound()

        payload = json.loads(request.POST['payload'])

        # This is a test payload GitHub sends when we add a new hook.
        # It does not contain the payload we expect, so just ignore it.
        if 'zen' in payload:
            return HttpResponse()

        request.payload = payload


class SignatureMiddleware(object):
    """
    Verifies that an HTTP request was really sent from GitHub by verifying that
    the contents of the X-Hub-Signature header (a SHA1 HMAC of the request
    body) matches our own calculation.
    """

    def process_request(self, request):
        github_signature = request.META.get('HTTP_X_HUB_SIGNATURE', '')
        computed_signature = 'sha1=%s' % \
                             hmac.new(settings.GITHUB_HOOK_SECRET,
                                      request.body, hashlib.sha1).hexdigest()
        if not constant_time_compare(github_signature, computed_signature):
            return HttpResponseNotFound()
