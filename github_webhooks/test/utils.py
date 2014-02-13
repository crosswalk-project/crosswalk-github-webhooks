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


def mock_pull_request_payload():
    """
    Returns a Pull Request payload with a reasonable amount of fields present
    in an actual payload for testing.
    Callers can later override the values in the dictionary to their liking.
    """
    return {
        'action': 'opened',
        'pull_request': {
            'number': 42,
            'patch_url': 'https://path/to/42.patch',
            'title': 'Hello world',
            'body': 'some description',
            'html_url': 'http://pr.com',
            'user': {
                'login': 'rakuco',
                'html_url': 'http://rakuco.com',
            },
            'head': {
                'sha': 'deadbeef',
                'repo': {
                    'name': 'crosswalk-fork',
                    'full_name': 'rakuco/crosswalk-fork',
                    'html_url': 'http://fork.com',
                },
            },
            'base': {
                'ref': 'master',
                'repo': {
                    'name': 'crosswalk',
                    'full_name': 'crosswalk-project/crosswalk',
                },
            },
        },
    }
