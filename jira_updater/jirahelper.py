# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from jira.client import JIRA
from jira.exceptions import JIRAError
from django.conf import settings
import logging

open_comment_template = \
    u'(i) [{user_id}|{user_url}] referenced this issue in project' \
    u' [{repo_name}|{repo_url}]:\n\n*[Pull Request ' \
    u'{pr_number}|{pr_url}]* _"{pr_title}"_'

close_comment_template = \
    u'(/) [{user_id}|{user_url}] resolved this issue with ' \
    u'*[Pull Request {pr_number}|{pr_url}]*'


class JiraHelper:
    """
    Connects to Jira server and provides high-level methods
    to comment and resolve issues based on data from a PR
    """
    def __init__(self):
        self.jira = None

    def _jira(self):
        """
        Initialize the connection to the JIRA server
        """
        if self.jira is None:
            options = {
                'server': settings.JIRA_SERVER,
                'verify': settings.JIRA_VERIFY_SSL
            }
            self.jira = JIRA(options, basic_auth=(settings.JIRA_USER,
                                                  settings.JIRA_PASSWORD))
        return self.jira

    def _get_resolve_transition(self, issue):
        """
        Returns the JIRA transition corresponding to "Resolve" for the given
        issue, or None if such a transition does not exist for the issue at its
        current state.
        """
        for transition in self._jira().transitions(issue):
            if transition['name'] == settings.JIRA_TRANSITION_RESOLVE_NAME:
                return transition
        return None

    def comment_issue(self, issue_id, payload):
        comment = open_comment_template.format(
            user_id=payload['pull_request']['user']['login'],
            user_url=payload['pull_request']['user']['html_url'],
            repo_name=payload['pull_request']['head']['repo']['name'],
            repo_url=payload['pull_request']['head']['repo']['html_url'],
            pr_number=payload['pull_request']['number'],
            pr_url=payload['pull_request']['html_url'],
            pr_title=payload['pull_request']['title'])

        try:
            self._jira().add_comment(issue_id, comment)
        except JIRAError as e:
            logging.error('Could not comment issue %s: %s' %
                          (issue_id, e.text))

    def resolve_issue(self, issue_id, payload):
        comment = close_comment_template.format(
            user_id=payload['pull_request']['user']['login'],
            user_url=payload['pull_request']['user']['html_url'],
            pr_number=payload['pull_request']['number'],
            pr_url=payload['pull_request']['html_url'])

        issue = self._jira().issue(issue_id)
        resolve_transition = self._get_resolve_transition(issue)

        if resolve_transition is None:
            logging.warn('Issue %s does not have a valid transition to '
                         'the "Resolve" state.' % issue_id)
            return

        try:
            self._jira().add_comment(issue_id, comment)
            self._jira().transition_issue(
                issue,
                resolve_transition['id'],
                resolution={'id': settings.JIRA_RESOLUTION_FIXED_ID})
        except JIRAError as e:
            logging.error('Could not resolve issue %s: %s' %
                          (issue_id, e.text))
