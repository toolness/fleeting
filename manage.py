import os
import argparse
import subprocess

from fleeting import app, Project

def cmd_runserver(args):
    "Run development server."

    app.config.update(
        SECRET_KEY='development',
        SERVER_NAME='localhost:5000'
    )
    app.run(debug=True)

def cmd_test(args):
    "Run test suite."

    errno = subprocess.call([
        'coverage', 'run',
        '--source', 'fleeting',
        '-m', 'unittest', 'discover'
    ])
    if errno: raise SystemExit(errno)
    errno = subprocess.call([
        'coverage', 'report',
        '--fail-under', '100', '-m'
    ])
    if not errno:
        print "All tests succeeded with 100% code coverage."
    raise SystemExit(errno)

def cmd_project(parser):
    "Manage EC2 instances."

    def cmd_status(args):
        "Show status information about an instance."

        print args.project.get_instance_status(args.slug)

    def cmd_destroy(args):
        "Destroy an instance."

        print args.project.destroy_instance(args.slug)

    def cmd_cleanup(args):
        "Cleanup unneeded autoscale groups and launch configs."

        deleted, errors = args.project.cleanup_instances()
        print "%d object(s) deleted, %d errors." % (deleted, errors)

    def cmd_list(args):
        "List EC2 instances."

        for inst in args.project.get_instances():
            print repr(inst)

    def cmd_create(args):
        "Create an EC2 instance."

        print args.project.create_instance(
            slug=args.slug,
            git_user=args.user,
            git_branch=args.branch,
            key_name=args.key_name,
            notify_topic=args.notify_topic,
            security_groups=[args.security_group]
        )

    subparsers = parser.add_subparsers()

    parser.add_argument('--project', '-p',
                        help='project id (default is openbadges)',
                        default='openbadges')
    create = subparsers.add_parser('create', help=cmd_create.__doc__)
    create.add_argument('slug', help='unique slug id to create')
    create.add_argument('user', help='git user to pull repo from')
    create.add_argument('branch', help='branch to deploy')
    create.add_argument('--key-name', '-k', help='aws crypto key to use',
                        default=os.environ.get('AWS_KEY_NAME'))
    create.add_argument('--notify-topic', '-n', help='notify topic arn',
                        default=os.environ.get('AWS_NOTIFY_TOPIC'))
    create.add_argument('--security-group', '-s', help='security group name',
                        default=os.environ.get('AWS_SECURITY_GROUP',
                                               'default'))
    create.set_defaults(func=cmd_create)

    cleanup = subparsers.add_parser('cleanup', help=cmd_cleanup.__doc__)
    cleanup.set_defaults(func=cmd_cleanup)

    lister = subparsers.add_parser('list', help=cmd_list.__doc__)
    lister.set_defaults(func=cmd_list)

    destroy = subparsers.add_parser('destroy', help=cmd_destroy.__doc__)
    destroy.add_argument('slug', help='unique slug id to destroy')
    destroy.set_defaults(func=cmd_destroy)

    status = subparsers.add_parser('status', help=cmd_status.__doc__)
    status.add_argument('slug', help='unique slug id to query')
    status.set_defaults(func=cmd_status)

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    rs = subparsers.add_parser('runserver', help=cmd_runserver.__doc__)
    rs.set_defaults(func=cmd_runserver)

    test = subparsers.add_parser('test', help=cmd_test.__doc__)
    test.set_defaults(func=cmd_test)

    cmd_project(subparsers.add_parser('project', help=cmd_project.__doc__))

    args = parser.parse_args()

    if 'project' in args:
        args.project = Project(args.project)

    args.func(args)

if __name__ == '__main__':
    main()
