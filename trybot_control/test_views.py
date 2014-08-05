# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client

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
