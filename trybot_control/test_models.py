# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import mock

from django.test import TestCase
from django.test.utils import override_settings

from trybot_control.models import *


class PullRequestTestCase(TestCase):
    @mock.patch('requests.post')
    def test_report_build_status(self, mock_request):
        pr = PullRequest.objects.create(
            number=42,
            head_sha='deadbeef',
            base_repo_path='foo/bar',
            head_repo_path='user/bar-fork',
            comment_id=1234,
            status=STATUS_SUCCESS
        )

        pr.report_build_status()

        data = {'state': STATUS_SUCCESS,
                'description': 'All bots are green',
                'target_url': ''}
        url = 'https://api.github.com/repos/foo/bar/statuses/deadbeef'

        self.assertEqual(mock_request.call_count, 1)
        self.assertEqual(
            mock_request.call_args,
            mock.call(url, data=json.dumps(data), auth=mock.ANY)
        )

    @mock.patch('requests.patch')
    @override_settings(TRYBOT_BASE_URL='http://tryb.ot')
    def test_report_builder_statuses(self, mock_request):
        pr = PullRequest.objects.create(
            number=42,
            head_sha='deadbeef',
            base_repo_path='user/repo',
            head_repo_path='another_user/bar-fork',
            comment_id=1234,
            status=STATUS_SUCCESS
        )

        TrybotBuild.objects.create(
            pull_request=pr,
            builder_name='crosswalk-linux',
            build_number=42,
            status=STATUS_PENDING
        )
        TrybotBuild.objects.create(
            pull_request=pr,
            builder_name='Crosswalk Tizen',
            build_number=34,
            status=STATUS_SUCCESS
        )

        pr.report_builder_statuses()

        url = 'https://api.github.com/repos/user/repo/issues/comments/1234'
        message = '''Testing patch series with another_user/bar-fork@deadbeef as its head.

Bot | Status
--- | ------
crosswalk-linux | [In Progress](http://tryb.ot/builders/crosswalk-linux/builds/42)
Crosswalk Tizen | [**SUCCESS** :green_heart:](http://tryb.ot/builders/Crosswalk Tizen/builds/34)
'''

        self.assertEqual(mock_request.call_count, 1)
        self.assertEqual(mock_request.call_args,
                         mock.call(url, auth=mock.ANY,
                                   data=json.dumps({'body': message})))

        TrybotBuild.objects.create(
            pull_request=pr,
            builder_name='XWalk Windows',
            build_number=3,
            status=STATUS_FAILURE
        )
        pr.report_builder_statuses()

        message += 'XWalk Windows | [**FAILED** :broken_heart:](http://tryb.ot/builders/XWalk Windows/builds/3)\n'

        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(mock_request.call_args,
                         mock.call(url, auth=mock.ANY,
                                   data=json.dumps({'body': message})))
