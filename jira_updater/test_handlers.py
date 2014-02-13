# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from mock import patch, ANY, Mock

from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.conf import settings

from github_webhooks.test.utils import GitHubEventClient
from github_webhooks.test.utils import mock_pull_request_payload
from jira_updater.handlers import handle_pull_request
from jira_updater.handlers import search_issues


class JiraUpdaterTestCase(TestCase):
    def setUp(self):
        settings.JIRA_PROJECT = 'PROJ'

    def test_regexp_no_issue(self):
        text = 'Text with no issue'
        issues = search_issues(text)
        self.assertEqual(issues, [])

    def test_regexp_mention_issue(self):
        text = 'Text mentioning issue PROJ-1'
        issues = search_issues(text)
        self.assertEqual(len(issues), 1)

    @patch('jira_updater.jirahelper.JIRA')
    def test_no_issue(self, jira_mock):
        payload = mock_pull_request_payload()
        payload['pull_request']['body'] = 'This PR does not fix any issue'
        handle_pull_request(None, payload=payload)
        self.assertEqual(jira_mock.called, False)

    @patch('jira_updater.jirahelper.JIRA')
    def test_comment_issue(self, jira_mock):
        payload = mock_pull_request_payload()
        payload['pull_request']['body'] = \
            'This PR will resolve the issue'\
            'mentioned below:'\
            '\n'\
            'BUG=https://crosswalk-project.org/jira/bug=PROJ-2'
        handle_pull_request(None, payload=payload)
        jira_mock.return_value.add_comment.assert_called_with('PROJ-2', ANY)

    @patch('jira_updater.jirahelper.JIRA')
    def test_resolve_issue(self, jira_mock):
        payload = mock_pull_request_payload()
        payload['action'] = 'closed'
        payload['pull_request']['body'] = \
            'This PR will close the issue'\
            'mentioned below:'\
            '\n'\
            'BUG=https://crosswalk-project.org/jira/bug=PROJ-2'
        payload['pull_request']['merged'] = True
        issue_mock = Mock()
        jira_mock.return_value.issue.return_value = issue_mock
        handle_pull_request(None, payload=payload)
        jira_mock.return_value.issue.assert_called_with('PROJ-2')
        jira_mock.return_value.add_comment.assert_called_with('PROJ-2', ANY)
        jira_mock.return_value.transition_issue.assert_called_with(
            issue_mock,
            settings.JIRA_TRANSITION_RESOLVE_ID,
            resolution={'id': settings.JIRA_RESOLUTION_FIXED_ID}
            )
