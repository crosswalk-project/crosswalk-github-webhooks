# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from mock import patch, ANY, Mock

from django.core.urlresolvers import reverse
from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from django.test.utils import override_settings

from github_webhooks.test.utils import GitHubEventClient
from github_webhooks.test.utils import mock_pull_request_payload
from jira_updater.handlers import JiraHelper
from jira_updater.handlers import handle_pull_request
from jira_updater.handlers import search_issues


class JiraUpdaterTestCase(TestCase):
    def setUp(self):
        settings.JIRA_PROJECT = 'PROJ'
        self.client = GitHubEventClient()
        self.url = reverse('jira_updater.views.handle_pull_request')

    @patch('jira_updater.jirahelper.JIRA')
    def test_non_ascii_pr_title(self, jira_mock):
        helper = JiraHelper()

        payload = mock_pull_request_payload()
        payload['pull_request']['title'] = 'Standard title'
        helper.comment_issue('PROJ-42', payload)
        jira_mock.return_value.add_comment.assert_called_with('PROJ-42', ANY)

        payload = mock_pull_request_payload()
        payload['pull_request']['title'] = u'Non-ASCII \u2018title\u2019'
        helper.comment_issue('PROJ-42', payload)
        jira_mock.return_value.add_comment.assert_called_with('PROJ-42', ANY)

    def test_regexp_no_issue(self):
        text = 'Text with no issue'
        issues = search_issues(text)
        self.assertEqual(issues, [])

    def test_regexp_mention_issue(self):
        text = 'Text mentioning issue PROJ-1'
        issues = search_issues(text)
        self.assertEqual(len(issues), 1)

    def test_should_resolve_issue(self):
        text = 'Pull request. Does not reference any issues.'
        issues = search_issues(text)
        self.assertEqual(len(issues), 0)

        text = 'Related, does not solve, a single issue, PROJ-789.'
        issues = search_issues(text)
        self.assertItemsEqual(issues,
                              [{'id': 'PROJ-789', 'resolve': False}])

        text = 'Related but does not solve PROJ-1234 and\nPROJ-456.'
        issues = search_issues(text)
        self.assertItemsEqual(issues,
                              [{'id': 'PROJ-1234', 'resolve': False},
                               {'id': 'PROJ-456', 'resolve': False}])

        text = 'This is related to PROJ-1234 and\nFOOBAR-456.'
        issues = search_issues(text)
        self.assertItemsEqual(issues,
                              [{'id': 'PROJ-1234', 'resolve': False}])

        text = 'Patch to fix PROJ-789, related to PROJ-23.\n\nBUG=PROJ-789'
        issues = search_issues(text)
        self.assertItemsEqual(issues,
                              [{'id': 'PROJ-789', 'resolve': True},
                               {'id': 'PROJ-23', 'resolve': False}])

        text = 'Bug fix.\n\nBUG=PROJ-123\nBUG=PROJ-456'
        issues = search_issues(text)
        self.assertItemsEqual(issues,
                              [{'id': 'PROJ-123', 'resolve': True},
                               {'id': 'PROJ-456', 'resolve': True}])

        text = 'Wrong formatting. BUG=PROJ-123'
        issues = search_issues(text)
        self.assertItemsEqual(issues,
                              [{'id': 'PROJ-123', 'resolve': False}])

        text = 'A bug fix. BUG=PROJ-123\nBUG=PROJ-456'
        issues = search_issues(text)
        self.assertItemsEqual(issues,
                              [{'id': 'PROJ-123', 'resolve': False},
                               {'id': 'PROJ-456', 'resolve': True}])

    @patch('jira_updater.jirahelper.JIRA')
    def test_no_issue(self, jira_mock):
        payload = mock_pull_request_payload()

        payload['pull_request']['body'] = 'This PR does not fix any issue'
        response = self.client.post(self.url, payload)
        self.assertEqual(jira_mock.called, False)

        payload['pull_request']['body'] = None
        response = self.client.post(self.url, payload)
        self.assertEqual(jira_mock.called, False)

    @patch('jira_updater.jirahelper.JIRA')
    def test_comment_issue(self, jira_mock):
        payload = mock_pull_request_payload()
        payload['pull_request']['body'] = \
            'This PR will resolve the issue'\
            'mentioned below:'\
            '\n'\
            'BUG=https://crosswalk-project.org/jira/bug=PROJ-2'
        response = self.client.post(self.url, payload)
        jira_mock.return_value.add_comment.assert_called_with('PROJ-2', ANY)

    @override_settings(JIRA_TRANSITION_RESOLVE_NAME='Resolve')
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
        jira_mock.return_value.transitions.return_value = (
            {'id': '1', 'name': 'Triage'},
            {'id': '2', 'name': 'Resolve'},
        )
        response = self.client.post(self.url, payload)
        jira_mock.return_value.issue.assert_called_with('PROJ-2')
        jira_mock.return_value.transition_issue.assert_called_with(
            issue_mock,
            '2',
            comment=ANY,
            resolution={'id': settings.JIRA_RESOLUTION_FIXED_ID}
            )
        self.assertEqual(jira_mock.return_value.transitions.call_count, 1)
        self.assertEqual(jira_mock.return_value.add_comment.call_count, 0)
        self.assertEqual(jira_mock.return_value.transition_issue.call_count, 1)

        issue_mock = Mock()
        jira_mock.return_value.issue.return_value = issue_mock
        jira_mock.return_value.transitions.return_value = (
            {'id': '1', 'name': 'Triage'},
            {'id': '2', 'name': 'Close'},
            {'id': '5', 'name': 'New'},
        )
        response = self.client.post(self.url, payload)
        self.assertEqual(jira_mock.return_value.transitions.call_count, 2)
        self.assertEqual(jira_mock.return_value.add_comment.call_count, 0)
        self.assertEqual(jira_mock.return_value.transition_issue.call_count, 1)
