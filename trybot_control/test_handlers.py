# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import mock

from django.core.urlresolvers import reverse
from django.test import TestCase

from github_webhooks.test.utils import GitHubEventClient, mock_pull_request_payload
from trybot_control.models import *


class HandlePullRequestTestCase(TestCase):
    def setUp(self):
        self.client = GitHubEventClient()
        self.url = reverse('github_webhooks.views.dispatch_pull_request')

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_success(self, mock_requests_get, mock_requests_post):
        payload = mock_pull_request_payload()

        get_response = mock.Mock()
        get_response.status_code = 200
        get_response.text = '+++ some/file\n--- some/file\n+ new line\n'
        get_response.json.return_value = {'id': 3}
        mock_requests_get.return_value = get_response
        response = self.client.post(self.url, payload)
        self.assertEqual(PullRequest.objects.count(), 1)
        pr = PullRequest.objects.get(pk=1)
        self.assertEqual(pr.number, 42)
        self.assertEqual(pr.head_sha, 'deadbeef')
        self.assertEqual(pr.repo_path, 'crosswalk-project/crosswalk')
        self.assertEqual(pr.status, STATUS_PENDING)
        self.assertEqual(pr.needs_sync, True)

        payload['action'] = 'synchronize'
        payload['pull_request']['head']['sha'] = 'f00b4r'
        response = self.client.post(self.url, payload)
        self.assertEqual(PullRequest.objects.count(), 2)
        pr = PullRequest.objects.get(pk=2)
        self.assertEqual(pr.number, 42)
        self.assertEqual(pr.head_sha, 'f00b4r')
        self.assertEqual(pr.repo_path, 'crosswalk-project/crosswalk')
        self.assertEqual(pr.status, STATUS_PENDING)
        self.assertEqual(pr.needs_sync, True)

    @mock.patch('requests.get')
    def test_patch_fetch_error(self, mock_requests_get):
        payload = mock_pull_request_payload()

        mock_response = mock.Mock()
        mock_response.status_code = 404
        mock_requests_get.return_value = mock_response
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PullRequest.objects.count(), 0)

    def test_ignored_action(self):
        payload = mock_pull_request_payload()

        payload['action'] = 'closed'
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PullRequest.objects.count(), 0)

        payload['action'] = 'reopened'
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PullRequest.objects.count(), 0)
