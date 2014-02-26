# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import mock

from django.core.urlresolvers import reverse
from django.test import TestCase

from github_webhooks.test.utils import GitHubEventClient


class GitHubWebhooksTestCase(TestCase):
    def setUp(self):
        self.client = GitHubEventClient()
        self.url = reverse('github_webhooks.views.dispatch_pull_request')

    @mock.patch('github_webhooks.signals.pull_request_changed.send')
    def test_ping_payload(self, mock_pull_request_changed):
        payload = {
            'zen': 'Practicality beats purity.',
            'hook_id': 42,
        }

        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_pull_request_changed.call_count, 0)
