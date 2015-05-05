This is a collection of GitHub web hook handlers used by the Crosswalk project.

There are no templates because we just process events sent by GitHub and do not
need to show anything to users directly.

## jira_updater

This application watches the creation and closing of pull requests, and updates
JIRA tickets based on the occurence of certain keywords in the pull request
message.

## trybot_control

This application receives pull request events and talks to Buildbot so that a
patch is processed by our slaves whenever it is sent or updated. The results
are then posted back to the pull request as a comment.

Slow actions such as posting those comments are done asynchronously, as they
would otherwise block critical sections of the code. Instead, we rely on custom
commands that are run at any later time to do any sort of required processing.

For example, one could have a cron job that calls

    python manage.py sync_trybot_status

to update the pull request status on GitHub every N minutes.
