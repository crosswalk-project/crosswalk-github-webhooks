# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from django.core.management.base import BaseCommand
from django.conf import settings

from trybot_control.models import PullRequest, STATUS_PENDING


class Command(BaseCommand):
    help = 'Goes through the list of status updates sent by Buildbot and ' \
           'updates the related pull request with the new information.'

    def handle(self, *args, **options):
        for pull_request in PullRequest.objects.filter(needs_sync=True):
            pull_request.needs_sync = False
            pull_request.save()

            pull_request.report_builder_statuses()
            pull_request.report_build_status()

        # TrybotBuild entries with this pull request number will be deleted
        # automatically (Django's default behavior is ON DELETE CASCADE).
        PullRequest.objects.exclude(status=STATUS_PENDING).delete()
