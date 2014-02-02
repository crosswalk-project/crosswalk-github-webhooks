# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from django.conf.urls import patterns, include, url


urlpatterns = patterns('github_webhooks.views',
    url(r'^github-hooks/pull-request$', 'dispatch_pull_request'),
)

urlpatterns += patterns('',
    url(r'^trybot_control/', include('trybot_control.urls')),
)
