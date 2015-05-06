# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    url(r'^github-hooks/jira$',
        'jira_updater.views.handle_pull_request'),
    url(r'^github-hooks/trybot$',
        'trybot_control.views.handle_pull_request'),
)

urlpatterns += patterns('',
    url(r'^trybot_control/', include('trybot_control.urls')),
)
