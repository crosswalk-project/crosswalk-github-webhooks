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
from github_webhooks.test.utils import mock_pull_request_payload
from trybot_control.models import *


class BuildbotEventTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('trybot_control.views.buildbot_event')

    def test_buildStarted_event(self):
        PullRequest.objects.create(
            pk=3,
            number=97,
            head_sha=hashlib.sha1('somehash').hexdigest(),
            base_repo_path='crosswalk-project/crosswalk',
            head_repo_path='user/crosswalk-fork',
            comment_id=1234)

        packets = [{
            'event': 'buildStarted',
            'payload': {
                'build': {
                    'builderName': 'crosswalk-linux',
                    'number': 42,
                    'properties': [('issue', 97, '')],
                }
            }
        }]
        response = self.client.post(self.url, {'packets': json.dumps(packets)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TrybotBuild.objects.count(), 0)

        packets = [{
            'event': 'buildStarted',
            'payload': {
                'build': {
                    'builderName': 'crosswalk-linux',
                    'number': 42,
                    'properties': [('issue', 3, '')],
                }
            }
        }]
        response = self.client.post(self.url, {'packets': json.dumps(packets)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TrybotBuild.objects.count(), 1)
        build = TrybotBuild.objects.get(pk=1)
        self.assertEqual(build.pull_request.pk, 3)
        self.assertEqual(build.builder_name, 'crosswalk-linux')
        self.assertEqual(build.build_number, 42)
        self.assertEqual(build.status, STATUS_PENDING)

        packets = [{
            'event': 'buildStarted',
            'payload': {
                'build': {
                    'builderName': 'crosswalk-windows',
                    'number': 34,
                    'properties': [('issue', 3, '')],
                }
            }
        }]
        response = self.client.post(self.url, {'packets': json.dumps(packets)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TrybotBuild.objects.count(), 2)
        build = TrybotBuild.objects.get(pk=2)
        self.assertEqual(build.pull_request.pk, 3)
        self.assertEqual(build.builder_name, 'crosswalk-windows')
        self.assertEqual(build.build_number, 34)
        self.assertEqual(build.status, STATUS_PENDING)

    def test_buildFinished_event(self):
        pr = PullRequest.objects.create(
            pk=3,
            number=97,
            head_sha=hashlib.sha1('somehash').hexdigest(),
            base_repo_path='crosswalk-project/crosswalk',
            head_repo_path='user/crosswalk-fork',
            comment_id=1234)
        TrybotBuild.objects.create(
            pull_request=pr,
            builder_name='crosswalk-linux',
            build_number=42,
            status=STATUS_PENDING)
        TrybotBuild.objects.create(
            pull_request=pr,
            builder_name='crosswalk-windows',
            build_number=34,
            status=STATUS_PENDING)

        packets = [{
            'event': 'buildFinished',
            'payload': {
                'build': {
                    'builderName': 'crosswalk-linux',
                    'number': 42,
                    'properties': [('issue', 3, '')],
                }
            }
        }]
        response = self.client.post(self.url, {'packets': json.dumps(packets)})
        self.assertEqual(response.status_code, 200)
        build = TrybotBuild.objects.get(pk=1)
        self.assertEqual(build.pull_request.pk, 3)
        self.assertEqual(build.builder_name, 'crosswalk-linux')
        self.assertEqual(build.build_number, 42)
        self.assertEqual(build.status, STATUS_SUCCESS)

        packets = [{
            'event': 'buildFinished',
            'payload': {
                'build': {
                    'builderName': 'crosswalk-linux',
                    'number': 42,
                    'properties': [('issue', 3, '')],
                    'results': 1,
                }
            }
        }]
        response = self.client.post(self.url, {'packets': json.dumps(packets)})
        self.assertEqual(response.status_code, 200)
        build = TrybotBuild.objects.get(pk=1)
        self.assertEqual(build.pull_request.pk, 3)
        self.assertEqual(build.builder_name, 'crosswalk-linux')
        self.assertEqual(build.build_number, 42)
        self.assertEqual(build.status, STATUS_SUCCESS)

        packets = [{
            'event': 'buildFinished',
            'payload': {
                'build': {
                    'builderName': 'crosswalk-windows',
                    'number': 34,
                    'properties': [('issue', 3, '')],
                    'results': 2,
                }
            }
        }]
        response = self.client.post(self.url, {'packets': json.dumps(packets)})
        self.assertEqual(response.status_code, 200)
        build = TrybotBuild.objects.get(pk=2)
        self.assertEqual(build.pull_request.pk, 3)
        self.assertEqual(build.builder_name, 'crosswalk-windows')
        self.assertEqual(build.build_number, 34)
        self.assertEqual(build.status, STATUS_FAILURE)

    def test_buildsetFinished_event(self):
        pr = PullRequest.objects.create(
            pk=3,
            number=97,
            head_sha=hashlib.sha1('somehash').hexdigest(),
            base_repo_path='crosswalk-project/crosswalk',
            head_repo_path='user/crosswalk-fork',
            comment_id=1234)
        TrybotBuild.objects.create(
            pull_request=pr,
            builder_name='crosswalk-linux',
            build_number=42,
            status=STATUS_SUCCESS)
        TrybotBuild.objects.create(
            pull_request=pr,
            builder_name='crosswalk-windows',
            build_number=34,
            status=STATUS_FAILURE)

        self.assertEqual(pr.status, STATUS_PENDING)

        packets = [{
            'event': 'buildsetFinished',
            'payload': {
                'build': {
                    'properties': [('issue', 3, '')],
                    'results': 2,
                }
            }
        }]
        response = self.client.post(self.url, {'packets': json.dumps(packets)})
        self.assertEqual(response.status_code, 200)
        pr = PullRequest.objects.get(pk=3)
        self.assertEqual(pr.status, STATUS_FAILURE)

        packets = [{
            'event': 'buildsetFinished',
            'payload': {
                'build': {
                    'properties': [('issue', 3, '')],
                }
            }
        }]
        response = self.client.post(self.url, {'packets': json.dumps(packets)})
        self.assertEqual(response.status_code, 200)
        pr = PullRequest.objects.get(pk=3)
        self.assertEqual(pr.status, STATUS_SUCCESS)

    def test_wrong_payload(self):
        # No data.
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 400)

        # No 'packets' key in request.POST.
        response = self.client.post(self.url, {'wrongkey': 'value'})
        self.assertEqual(response.status_code, 400)

        # Packets with no 'payload' key are just ignored.
        packets = [{
            'event': 'buildFinished',
            'some key': 'no payload key',
        }]
        response = self.client.post(self.url, {'packets': json.dumps(packets)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PullRequest.objects.count(), 0)
        self.assertEqual(TrybotBuild.objects.count(), 0)

        # Packets with an event we are not interested in are just ignored.
        packets = [{
            'event': 'ignored event',
            'payload': 'some payload'
        }]
        response = self.client.post(self.url, {'packets': json.dumps(packets)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PullRequest.objects.count(), 0)
        self.assertEqual(TrybotBuild.objects.count(), 0)

        # Packets with no 'issue' property are just ignored.
        packets = [{
            'event': 'buildFinished',
            'payload': {
                'build': {
                    'properties': [
                        ('propname', 'value', 'no issue'),
                    ]
                }
            }
        }]
        response = self.client.post(self.url, {'packets': json.dumps(packets)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PullRequest.objects.count(), 0)
        self.assertEqual(TrybotBuild.objects.count(), 0)

        # Packets referencing a non-existent issue are just ignored.
        packets = [{
            'event': 'buildFinished',
            'payload': {
                'build': {
                    'properties': [
                        ('issue', 5, ''),
                    ]
                }
            }
        }]
        response = self.client.post(self.url, {'packets': json.dumps(packets)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PullRequest.objects.count(), 0)
        self.assertEqual(TrybotBuild.objects.count(), 0)


class PullRequestTests(TestCase):
    def setUp(self):
        self.client = GitHubEventClient()
        self.url = reverse('trybot_control.views.handle_pull_request')

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_trybot_payload(self, mock_requests_get, mock_requests_post):
        get_response = mock.Mock()
        get_response.status_code = 200
        get_response.text = '+++ some/file\n--- some/file\n+ new line\n'
        get_response.json.return_value = {'id': 3}
        mock_requests_get.return_value = get_response

        # One mock for each requests.post() call in the handler.
        post_response_comment = mock.Mock()
        post_response_comment.json.return_value = {'id': 1234}
        post_response_send_to_trybot = mock.Mock()

        mock_requests_post.side_effects = (post_response_comment,
                                           post_response_send_to_trybot)

        payload = mock_pull_request_payload()
        payload['pull_request']['base']['ref'] = 'crosswalk-4'
        response = self.client.post(self.url, payload)
        self.assertEqual(PullRequest.objects.count(), 0)
        self.assertEqual(mock_requests_get.call_count, 0)
        self.assertEqual(mock_requests_post.call_count, 0)

        payload = mock_pull_request_payload()
        response = self.client.post(self.url, payload)
        self.assertEqual(PullRequest.objects.count(), 1)
        self.assertEqual(mock_requests_post.call_count, 3)
        payload = mock_requests_post.call_args[1]['data']
        expected_payload = {'user': u'rakuco',
                            'name': u'Hello world',
                            'email': 'noreply@01.org',
                            'revision': u'deadbeef',
                            'project': u'crosswalk',
                            'repository': u'crosswalk',
                            'branch': u'master',
                            'patch': '+++ some/file\n--- some/file\n+ new line\n',
                            'issue': PullRequest.objects.get(pk=1).pk}
        self.assertEqual(payload, expected_payload)

        # FIXME(rakuco): Remove this part of the test once the 'crosswalk-lite'
        # hackish check is removed from handlers.py.
        payload = mock_pull_request_payload()
        payload['pull_request']['base']['ref'] = 'crosswalk-lite'
        response = self.client.post(self.url, payload)
        self.assertEqual(PullRequest.objects.count(), 2)
        self.assertEqual(mock_requests_post.call_count, 6)
        payload = mock_pull_request_payload()
        payload['pull_request']['base']['repo']['name'] = 'v8-crosswalk'
        payload['pull_request']['base']['ref'] = 'crosswalk-lite'
        response = self.client.post(self.url, payload)
        self.assertEqual(PullRequest.objects.count(), 2)
        self.assertEqual(mock_requests_post.call_count, 6)

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
        self.assertEqual(pr.base_repo_path, 'crosswalk-project/crosswalk')
        self.assertEqual(pr.head_repo_path, 'rakuco/crosswalk-fork')
        self.assertEqual(pr.status, STATUS_PENDING)
        self.assertEqual(pr.needs_sync, True)

        payload['action'] = 'synchronize'
        payload['pull_request']['head']['sha'] = 'f00b4r'
        response = self.client.post(self.url, payload)
        self.assertEqual(PullRequest.objects.count(), 2)
        pr = PullRequest.objects.get(pk=2)
        self.assertEqual(pr.number, 42)
        self.assertEqual(pr.head_sha, 'f00b4r')
        self.assertEqual(pr.base_repo_path, 'crosswalk-project/crosswalk')
        self.assertEqual(pr.head_repo_path, 'rakuco/crosswalk-fork')
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
