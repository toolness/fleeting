import os
import argparse
import subprocess

from fleeting import app

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

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    rs = subparsers.add_parser('runserver', help=cmd_runserver.__doc__)
    rs.set_defaults(func=cmd_runserver)

    test = subparsers.add_parser('test', help=cmd_test.__doc__)
    test.set_defaults(func=cmd_test)

    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
