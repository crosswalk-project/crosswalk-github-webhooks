# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import hmac
import json
import urllib

from django.conf import settings
from django.test.client import BOUNDARY, Client, encode_multipart


class GitHubEventClient(Client):
    """
    A django.test.client.Client subclass that takes care of adding a
    proper X-Hub-Signature header to requests that are supposed to be
    signed by GitHub.
    """
    def post(self, path, data, *args, **kwargs):
        payload = {'payload': json.dumps(data)}
        encoded_multipart = encode_multipart(BOUNDARY, payload)

        signature = hmac.new(settings.GITHUB_HOOK_SECRET,
                             encoded_multipart,
                             hashlib.sha1)

        return super(GitHubEventClient, self).post(
            path,
            data=payload,
            HTTP_X_HUB_SIGNATURE='sha1=%s' % signature.hexdigest(),
            *args,
            **kwargs
        )
