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
  to `http`, but you can set it to `https` if needed. The server will
  automatically redirect any accesses via the other scheme to this
  preferred scheme.

* **ORIGINATING_SCHEME_HEADER** is the header that contains the
  value of the actual scheme (http or https) being used to access the
  server, if any. For instance, Heroku uses `X-Forwarded-Proto`.

* **AWS_NOTIFY_TOPIC** is the SNS Topic ARN that will be published to
  whenever Amazon finishes terminating an instance. The `/update` endpoint
  of the Fleeting server can be manually subscribed to this topic, which
  will allow it to properly clean up resources that are no longer needed
  after an instance is terminated. This variable is optional, but
  recommended.

* **REDIS_URL** (or **REDISTOGO_URL**) is the url to a redis instance,
  such as `redis://localhost:6379`. If provided, the app will use this
  redis instance for temporary storage. Otherwise, the app will use an
  in-process cache. If your server is pre-forking, or you're otherwise
  scaling this app via the process model, you should use redis.

## Deployment

The server was designed as a [12-factor app][] to run on Heroku.
Redis is needed if you have more than one process running the app.

## Adding More Projects

You'll need to add a file to the `fleeting/projects` directory. The
name of the file without the extension comprises the project [slug][]. The
easiest way to add a new project is by copying an existing file in that
directory and modifying it as needed.

Each file is actually a [Jinja][] template for an executable shell
script. The script also contains special metadata embedded in comments,
which Fleeting uses to determine parameters of the deployment.

### Jinja Context Variables

The following Jinja context variables are defined when a project script is
being generated for a deployment:

* **GIT_BRANCH** is the git branch name being deployed.
* **GIT_USER** is the github user whose repository is being deployed.

Here's an example of the context variables in use:

```
git clone --recursive -b {{GIT_BRANCH}} \
  git://github.com/{{GIT_USER}}/butter.git
```

### Project Metadata

Project metadata should be embedded in comments and always begins with
the string `fleeting-meta:`. The following variables should be declared:

* **name** is the human-readable name of the project.
* **repo** is the github repository where the canonical project is
  stored, in `user/repo` format.
* **image-id** is the EC2 [AMI][] to use when deploying branches of
  the project.
* **instance-type** is the EC2 [instance type][] to use when deploying
  branches of the project.
* **ready-url** is the URL that returns a 200 OK when the deployment is
  ready to be used. Typically, this is the front page of a website. The
  text `localhost` in this string is automatically replaced with the
  domain name that the branch has been deployed at.

Here's an example of this metadata being defined:

```
# fleeting-meta:name          = Popcorn Maker
# fleeting-meta:repo          = mozilla/butter
# fleeting-meta:image-id      = ami-2bb7d442
# fleeting-meta:instance-type = t1.micro
# fleeting-meta:ready-url     = http://localhost:8888/
```

## Limitations

There are a number of limitations right now.

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
  [Jinja]: http://jinja.pocoo.org/
  [AMI]: https://aws.amazon.com/amis/
  [instance type]: http://aws.amazon.com/ec2/instance-types/
  [12-factor app]: http://www.12factor.net/
