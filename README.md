[![Build Status](https://travis-ci.org/toolness/fleeting.png?branch=master)](https://travis-ci.org/toolness/fleeting)

Fleeting is a simple server that allows people to easily spin up
experimental project branches in short-lived EC2 instances.

## Prerequisites

This is a [Flask][] app. You'll need Python 2.7, and preferably
[virtualenv][]. You'll also want to sign up to [Amazon Web Services][aws]
if you haven't already.

## Quick Start

I recommend using a [virtualenv][] for local development.

    git clone git@github.com:toolness/fleeting.git
    cd fleeting
    virtualenv venv --distribute
    source bin/activate
    pip install -r requirements.dev.txt --use-mirrors
    python manage.py test

At this point, you'll want to define environment variables that provide
the app with information about your AWS credentials.

When developing, you can do this by pasting the following into an
`.env` file at the root of your repository:

```
AWS_KEY_NAME=<put aws crypto key name here>
AWS_SECURITY_GROUP=<put aws security group name here>
AWS_SECRET_ACCESS_KEY=<put aws secret access key here>
AWS_ACCESS_KEY_ID=<put aws access key id here>
```

Alternatively, you can define those variables in your environment.

Once you've done that, run `python manage.py runserver` and visit 
http://localhost:5000/.

## Environment Variables

These are the environment variables used by the app.

* **AWS_KEY_NAME** is the name of the AWS key pair to initialize 
  newly-spawned EC2 instances with. For more information, see
  [Getting a Key Pair][keypair] in the AWS documentation.

* **AWS_SECURITY_GROUP** is the name of the AWS security group
  that newly-spawned EC2 instances are assigned to. You'll want to
  make sure that this group allows external access to the port that
  your project exposes itself at. For more information, see
  [Amazon EC2 Security Groups][secgroup] in the AWS documentation.

* **AWS_SECRET_ACCESS_KEY** is your AWS secret access key. For more
  information, see [Getting Your AWS Access Identifiers][access] in
  the AWS documentation.

* **AWS_ACCESS_KEY_ID** is your AWS access key ID.  For more
  information, see [Getting Your AWS Access Identifiers][access] in
  the AWS documentation.

* **SERVER_NAME** is the hostname and, if applicable, the port number
  which Fleeting will be accessible at. Example values are
  `localhost:5000` or `enigmatic-beyond-4959.herokuapp.com`.

* **SERVER_SCHEME** is the protocol used to access Fleeting. It defaults
  to `http`, but you can set it to `https` if needed.

## Deployment

The server was designed to run on Heroku with no backend storage. It should
be runnable other places, too.

## Adding More Projects

You'll need to add a file to the `fleeting/projects` directory. The
name of the file without the extension comprises the project [slug][]. The
easiest way to add a new project is by copying an existing file in that
directory and modifying it as needed.

## Limitations

There are lots of limitations right now.

Currently, Fleeting instances auto-shutdown after 24 hours, and there's
no easy way to change it.

Anyone can spawn a Fleeting instance; they simply need to log in through
[Persona][]. Their email address is logged, but there isn't currently
any logic that whitelists email addresses or anything.

  [Flask]: http://flask.pocoo.org/
  [aws]: http://aws.amazon.com/
  [virtualenv]: http://www.virtualenv.org/
  [keypair]: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/generating-a-keypair.html
  [secgroup]: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-network-security.html
  [access]: http://docs.aws.amazon.com/fws/1.1/GettingStartedGuide/index.html?AWSCredentials.html
  [slug]: http://en.wikipedia.org/wiki/Clean_URL#Slug
  [Persona]: http://persona.org/
