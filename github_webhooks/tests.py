# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import json
import mock

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

from github_webhooks.test.utils import GitHubEventClient


class GitHubWebhooksTestCase(TestCase):
    def setUp(self):
        self.client = GitHubEventClient()
        self.url = reverse('github_webhooks.views.dispatch_pull_request')

    def test_no_github_signature(self):
        payload = json.dumps({'payload': {'a': 'b'}})
        response = Client().post(self.url, payload, 'application/json')
        self.assertEqual(response.status_code, 404)

    def test_wrong_github_signature(self):
        payload = json.dumps({'payload': {'a': 'b'}})
        signature = 'sha1=%s' % hashlib.sha1('wrong').hexdigest()
        response = Client().post(self.url, payload, 'application/json',
                                 HTTP_X_HUB_SIGNATURE=signature)
        self.assertEqual(response.status_code, 404)

    @mock.patch('github_webhooks.signals.pull_request_changed.send')
    def test_ping_payload(self, mock_pull_request_changed):
        payload = {
            'zen': 'Practicality beats purity.',
            'hook_id': 42,
        }

        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_pull_request_changed.call_count, 0)
