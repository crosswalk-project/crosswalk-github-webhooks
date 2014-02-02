# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import hmac
import json

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.http import require_POST

from github_webhooks.signals import pull_request_changed


# TODO(rakuco): This could be a middleware.
def is_valid_github_request(request):
    """
    Verifies that an HTTP request was really sent from GitHub by verifying that
    the contents of the X-Hub-Signature header (a SHA1 HMAC of the request
    body) matches our own calculation.
    """
    github_signature = request.META.get('HTTP_X_HUB_SIGNATURE', None)
    computed_signature = 'sha1=%s' % \
                         hmac.new(settings.GITHUB_HOOK_SECRET,
                                  request.body, hashlib.sha1).hexdigest()

    return github_signature == computed_signature


@require_POST
def dispatch_pull_request(request):
    """
    Receives a GitHub pull_request event triggered via a web hook and
    dispatches a signal with the request for interested handlers.
    """
    if not is_valid_github_request(request):
        return HttpResponseNotFound()

    payload = json.loads(request.POST['payload'])
    pull_request_changed.send(sender=None, payload=payload)

    return HttpResponse()
