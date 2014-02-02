# Copyright (c) 2014 Intel Corporation. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import django.dispatch

# A pull_request event has been sent by GitHub. |payload| is already a JSON.
pull_request_changed = django.dispatch.Signal(providing_args=['payload'])
