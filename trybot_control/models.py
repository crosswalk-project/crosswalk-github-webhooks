# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import requests

from django.conf import settings
from django.db import models


# These are GitHub status names.
# See https://developer.github.com/v3/repos/statuses/.
STATUS_PENDING = 'pending'
STATUS_FAILURE = 'failure'
STATUS_SUCCESS = 'success'


class TrybotBuild(models.Model):
    class Meta:
        unique_together = ('builder_name', 'build_number')

    pull_request = models.ForeignKey('PullRequest')
    builder_name = models.CharField(max_length=256)
    build_number = models.IntegerField()
    status = models.CharField(max_length=7, default=STATUS_PENDING, choices=(
        (STATUS_PENDING, 'In Progress'),
        (STATUS_FAILURE, '**FAILED** :broken_heart:'),
        (STATUS_SUCCESS, '**SUCCESS** :green_heart:'),
    ))


class PullRequest(models.Model):
    # Pull request number.
    number = models.IntegerField()
    # SHA1 of the tip of the branch to be merged.
    head_sha = models.CharField(max_length=40)
    # Pull request target repository path in the format "owner/repo".
    base_repo_path = models.CharField(max_length=256)
    # Pull request source repository path in the format "owner/repo".
    head_repo_path = models.CharField(max_length=256)
    # ID of the Trybot comment related to this pull request.
    comment_id = models.IntegerField()
    # State of the build as a whole (taking into account all builders).
    status = models.CharField(max_length=7, default=STATUS_PENDING, choices=(
        (STATUS_PENDING, 'Some bots are still building this pull request'),
        (STATUS_FAILURE, 'Some bots have failed to build this pull request'),
        (STATUS_SUCCESS, 'All bots are green'),
    ))
    # Whether a comment and status update needs to be sent.
    needs_sync = models.BooleanField(default=True)

    def report_build_status(self):
        """
        Sets a certain pull request's GitHub status (the status of all builds
        reported so far). Compare with |report_builder_statues|.
        """
        url = 'https://api.github.com/repos/%s/statuses/%s' % \
              (self.base_repo_path, self.head_sha)
        payload = {'state': self.status,
                   'description': self.get_status_display(),
                   'target_url': ''}
        requests.post(url, data=json.dumps(payload),
                      auth=(settings.GITHUB_USERNAME,
                            settings.GITHUB_ACCESS_TOKEN))

    def report_builder_statuses(self):
        """
        Creates or updates the Trybot comment in a pull request with the status
        of all builders registered so far.
        """
        message =  'Testing patch series with %s@%s as its head.\n\n' % \
                   (self.head_repo_path, self.head_sha)
        message += 'Bot | Status\n'
        message += '--- | ------\n'

        for builder in self.trybotbuild_set.all():
            message += '%s | [%s](%s/builders/%s/builds/%d)\n' % \
                       (builder.builder_name, builder.get_status_display(),
                        settings.TRYBOT_BASE_URL, builder.builder_name,
                        builder.build_number)

        url = 'https://api.github.com/repos/%s/issues/comments/%d' % \
              (self.base_repo_path, self.comment_id)
        requests.patch(url,
                       auth=(settings.GITHUB_USERNAME,
                             settings.GITHUB_ACCESS_TOKEN),
                       data=json.dumps({'body': message}))
