This is a collection of GitHub web hook handlers used by the Crosswalk project.

It is a somewhat unconventional Django website, as there are no templates and
the actual processing of the hooks is done in signal handlers.

In a nutshell, when a registered web hook is sent by GitHub to
`/github-webhooks/<event name>` it is parsed by one of the `dispatch_*` views
in the `github_webhooks` app, validated and the payload is sent in a signal to
all the interested applications, which can then talk to Buildbot, post a
comment in a JIRA ticket etc.

Slow actions such as performing network requests are not done in the views or
the signal handlers, as we would otherwise block critical sections of the code.
Instead, we rely on custom commands that are run at any later time to do any
sort of required processing.

For example, one could have a cron job that calls

    python manage.py sync_trybot_status

to update the pull request status on GitHub every N minutes.
