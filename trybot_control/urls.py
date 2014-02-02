# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^buildbot$', 'trybot_control.views.buildbot_event'),
)
