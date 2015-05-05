# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import hmac
import json
import logging
import requests

from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.views.decorators.http import require_POST

from github_webhooks.decorators import add_github_payload, require_github_signature
from trybot_control.models import *


def parse_buildbot_packet(packet):
    """
    Parses the JSON sent by a Buildbot HTTP Status Push and returns a
    dictionary containing the following keys:
    - event_name: Whatever is in the packet's "event" field.
    - status: None if the package does not have a "results" field, otherwise a
              corresponding models.STATUS_* value.
    - data: Whatever is in the packet's "build" field.
    - pull_request: A PullRequest object obtained from the "issue" property.
    If parsing fails, ValueError is raised with an appropriate error message.
    """
    if 'event' not in packet:
        raise ValueError('Got a packet without an "event" field.')
    if 'payload' not in packet:
        raise ValueError('Got a packet without a "payload" field.')
    if 'build' not in packet['payload']:
        raise ValueError('Got a packet without a "build" field.')
    if 'properties' not in packet['payload']['build']:
        raise ValueError('Got a packet without a "properties" field.')

    try:
        build = packet['payload']['build']
        properties = dict([(k, v) for k, v, _ in build['properties']])
        pull_request = PullRequest.objects.get(pk=properties['issue'])
    except ObjectDoesNotExist:
        raise ValueError('Pull request with id=%d does not exist.' % \
                         properties['issue'])
    except KeyError:
        raise ValueError('Got a packet without an "issue" property.')

    # Buildbot status codes:
    # 0=Success, 1=Warnings, 2=Failure, 3=Skipped, 4=Exception, 5=Retry
    status = build.get('results', 0)
    if status < 2:
        status = STATUS_SUCCESS
    else:
        status = STATUS_FAILURE

    return {'event_name': packet['event'],
            'status': status,
            'data': build,
            'pull_request': pull_request}


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


@require_POST
def buildbot_event(request):
    """
    Receives a payload from Buildbot with events relevant to us (when a build
    starts or finishes, for example).
    Note that contrary to GitHub, Buildbot does not sign its messages so this
    view should only receive requests from localhost (or another trusted
    source).
    """
    if 'packets' not in request.POST:
        logging.warn('POST from Buildbot did not contain a "packets" field.')
        return HttpResponseBadRequest()

    packets = json.loads(request.POST['packets'])

    for packet in packets:
        # We are consciously returning HTTP 200 even when an invalid packet is
        # sent because Buildbot will keep retrying to send the same packets
        # when it receives an error response.
        try:
            packet = parse_buildbot_packet(packet)
        except ValueError, e:
            logging.warn(e)
            continue

        event_name = packet['event_name']
        status = packet['status']
        data = packet['data']
        pull_request = packet['pull_request']

        if event_name == 'buildStarted':
            TrybotBuild.objects.create(pull_request=pull_request,
                                       builder_name=data['builderName'],
                                       build_number=data['number'],
                                       status=STATUS_PENDING)
        elif event_name == 'buildFinished':
            build = TrybotBuild.objects.get(builder_name=data['builderName'],
                                            build_number=data['number'])
            # 'results' is not set when the build finishes successfully.
            if status is None:
                build.status = STATUS_SUCCESS
            else:
                build.status = status
            build.save()
        elif event_name == 'buildsetFinished':
            pull_request.status = status
        else:
            logging.warn('Got a packet with an unknown event type "%s".' % \
                         packet.event)
            continue

        pull_request.needs_sync = True
        pull_request.save()

    return HttpResponse()


@require_POST
@require_github_signature
@add_github_payload
def handle_pull_request(request):
    payload = request.payload

    # 'reopened' is irrelevant for our purposes. 'closed' initially looks
    # relevant, but we cannot kill the trybot builds in the middle: we need to
    # wait for them to complete and only then remove the pull request from the
    # database and update the status.
    if payload['action'] not in ('opened', 'synchronize'):
        logging.warn('Ignoring action type "%s".' % payload['action'])
        return HttpResponse()

    pull_request = payload['pull_request']

    # FIXME(rakuco): Replace the 'crosswalk-lite' hackish check below with a
    # proper flow where a comment gets posted only if there are builders to
    # process the patch on the right branch.
    target_project = pull_request['base']['repo']['name']
    target_branch = pull_request['base']['ref']
    if target_project == 'crosswalk':
        if target_branch not in ('master', 'crosswalk-lite'):
            return HttpResponse()
    else:
        if target_branch != 'master':
            return HttpResponse()

    trybot_payload = make_trybot_payload(payload['pull_request'])
    if trybot_payload is None:
        return HttpResponseServerError()

    pull_request_number = pull_request['number']
    base_repo_path = pull_request['base']['repo']['full_name']
    head_repo_path = pull_request['head']['repo']['full_name']
    sha = pull_request['head']['sha']

    comment_url = 'https://api.github.com/repos/%s/issues/%d/comments' % \
                  (base_repo_path, pull_request_number)
    message = 'The patch series with %s@%s as head will be tested soon.' % \
              (head_repo_path, sha)
    response = requests.post(comment_url,
                             auth=(settings.GITHUB_USERNAME,
                                   settings.GITHUB_ACCESS_TOKEN),
                             data=json.dumps({'body': message}))
    comment_id = response.json()['id']

    pr_object = PullRequest.objects.create(number=pull_request_number,
                                           head_sha=sha,
                                           base_repo_path=base_repo_path,
                                           head_repo_path=head_repo_path,
                                           comment_id=comment_id)
    pr_object.report_build_status()

    # FIXME(rakuco): This is a bit too fragile, we create this object in the
    # make_trybot_payload() call but it needs this to have all the information
    # Buildbot needs.
    trybot_payload['issue'] = pr_object.pk

    requests.post(settings.TRYBOT_SEND_PATCH_URL, data=trybot_payload)
    return HttpResponse()
