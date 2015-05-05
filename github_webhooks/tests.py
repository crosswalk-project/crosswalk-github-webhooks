# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import hashlib
import json
import mock

from django.test import RequestFactory
from django.test import TestCase

from github_webhooks.middleware import PayloadMiddleware
from github_webhooks.middleware import SignatureMiddleware


class PayloadMiddlewareTests(TestCase):
    def test_ping(self):
        request = RequestFactory().post('/ping')
        request.POST['payload'] = json.dumps({
            'zen': 'Practicality beats purity.',
            'hook_id': 42,
        })
        r = PayloadMiddleware().process_request(request)
        self.assertEqual(r.status_code, 200)

    def test_no_payload(self):
        request = RequestFactory().post('/no_payload')
        r = PayloadMiddleware().process_request(request)
        self.assertEqual(r.status_code, 404)


class SignatureMiddlewareTests(TestCase):
    def test_no_github_signature(self):
        request = RequestFactory().get('/no_signature')
        r = SignatureMiddleware().process_request(request)
        self.assertEqual(r.status_code, 404)

    def test_wrong_github_signature(self):
        request = RequestFactory().get('/wrong_signature')
        request.META['HTTP_X_HUB_SIGNATURE'] = 'sha1=%s' % \
                                               hashlib.sha1('xy').hexdigest()
        r = SignatureMiddleware().process_request(request)
        self.assertEqual(r.status_code, 404)
