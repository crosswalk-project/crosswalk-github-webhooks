# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Signal handlers for the event signals dispatched by the github_webhooks app.
"""

import json
import logging
import requests

from django.conf import settings
from django.dispatch import receiver

from github_webhooks.signals import pull_request_changed
from trybot_control.models import PullRequest


def make_trybot_payload(pull_request):
    """
    Gets any relevant data from a pull request JSON object sent by GitHub and
    uses that to build a dict with the keys used by try_job_base.py.
    """
    patch_response = requests.get(pull_request['patch_url'])
    if patch_response.status_code != 200:
        logging.error('Fetching %s from GitHub failed with status code %d.' % \
                      (pull_request['patch_url'], patch_response.status_code))
        return None

    return {
        'user': pull_request['user']['login'],
        'name': pull_request['title'],
        'email': 'noreply@01.org',
        'revision': pull_request['head']['sha'],
        'project': pull_request['base']['repo']['name'],
        'repository': pull_request['base']['repo']['name'],
        'branch': pull_request['base']['ref'],
        'patch': patch_response.text,
    }


@receiver(pull_request_changed)
def handle_pull_request(sender, **kwargs):
    payload = kwargs['payload']

    # 'reopened' is irrelevant for our purposes. 'closed' initially looks
    # relevant, but we cannot kill the trybot builds in the middle: we need to
    # wait for them to complete and only then remove the pull request from the
    # database and update the status.
    if payload['action'] not in ('opened', 'synchronize'):
        logging.warn('Ignoring action type "%s".' % payload['action'])
        return

    trybot_payload = make_trybot_payload(payload['pull_request'])
    if trybot_payload is None:
        return

    pull_request = payload['pull_request']
    pull_request_number = pull_request['number']
    repo_path = pull_request['base']['repo']['full_name']
    sha = pull_request['head']['sha']

    comment_url = 'https://api.github.com/repos/%s/issues/%d/comments' % \
                  (repo_path, pull_request_number)
    message = 'The patch series with %s as head will be tested soon.' % sha
    response = requests.post(comment_url,
                             auth=(settings.GITHUB_USERNAME,
                                   settings.GITHUB_ACCESS_TOKEN),
                             data=json.dumps({'body': message}))
    comment_id = response.json()['id']

    pr_object = PullRequest.objects.create(number=pull_request_number,
                                           head_sha=sha,
                                           repo_path=repo_path,
                                           comment_id=comment_id)

    # FIXME(rakuco): This is a bit too fragile, we create this object in the
    # make_trybot_payload() call but it needs this to have all the information
    # Buildbot needs.
    trybot_payload['number'] = pr_object.pk

    requests.post(settings.TRYBOT_SEND_PATCH_URL, data=trybot_payload)
