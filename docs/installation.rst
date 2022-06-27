Installation
============

Mesh Info requires Python 3.7+, RRDtool, and PostgreSQL libraries
(although it defaults to using SQLite).
The following instructions include installing those dependencies.

Installation instructions for Raspberry Pi OS
(tested on Bullseye, but Buster should work as well).
This will create a ``meshinfo`` user,
install the application to ``/opt/mesh-info`` as that user
(in a Python virtualenv),
and create ``/var/lib/mesh-info`` for storing the application data.

.. note::

    If you are interested in setting up Mesh Info for development,
    please see :doc:`contributing`.

.. code-block:: console

    $ sudo apt update
    $ sudo apt install -y libpq-dev librrd-dev python3 python3-dev python3-pip python3-venv
    $ sudo useradd meshinfo
    $ sudo mkdir /opt/mesh-info
    $ sudo chown -R meshinfo: /opt/mesh-info/
    # Login as the meshinfo user to run the following commands
    $ sudo -u meshinfo -i
    $ clone https://github.com/smsearcy/mesh-info.git /opt/mesh-info/src
    $ python3 -m venv /opt/mesh-info/
    # Activate the Python virtualenv for the next few commands
    $ . /opt/mesh-info/bin/activate
    (mesh-info) $ pip install -U pip setuptools wheel
    (mesh-info) $ pip install -r /opt/mesh-info/src/requirements.txt
    (mesh-info) $ pip install -e /opt/mesh-info/src
    # Run the database migrations
    (mesh-info) $ alembic -c /opt/mesh-info/src/alembic.ini upgrade head
    (mesh-info) $ deactivate
    $ exit

To run a test scan,
you can run the following
(optionally specifying the name or IP of the local node,
in case ``localnode.local.mesh`` does not resolve):

.. code-block:: console

    $ /opt/mesh-info/bin/meshinfo report [LOCAL_NODE]

If it is unable to connect to ``localnode.local.mesh``,
then you will need to create ``/opt/mesh-info/src/.env`` with the following
(using the node's address instead of 10.1.1.1)
for the collector service to run:

.. code-block::

    MESH_INFO_LOCAL_NODE="10.1.1.1"

.. tip::

   See :doc:`config` for more details and options.

You can also do a test of the poller/collector to confirm database access and data folder.
The ``--run-once`` option means it will poll the network once, save the results, and quit.

.. code-block:: console

    $ /opt/mesh-info/bin/meshinfo collector --run-once

While you could run the web service and collector via ``/opt/mesh-info/bin/meshinfo web`` and ``/opt/mesh-info/bin/meshinfo collecotr``,
it is advantageous to setup Systemd services to run automatically
and a NGINX reverse proxy in front of the Python application.

Systemd Services
----------------

Create the following files and run the ``systemctl`` commands below to setup Mesh Info as system services.

Based on `this documentation <https://docs.gunicorn.org/en/stable/deploy.html#systemd>`_.

``/etc/systemd/system/meshinfo-web.socket``

.. code-block:: ini

    [Unit]
    Description=Mesh Info Socket

    [Socket]
    ListenStream=/run/mesh-info.sock
    # Our service won't need permissions,
    # since it inherits the file descriptor by socket activation
    # so only NGINX daemon needs access
    SocketUser=www-data
    # Optionally restrict the socket permissions further
    #SocketMode=600

    [Install]
    WantedBy=sockets.target

``/etc/systemd/system/meshinfo-web.service``

.. code-block:: ini

    [Unit]
    Description=Mesh Info Web Service
    Requires=meshinfo-web.socket
    After=network.target

    [Service]
    Type=simple
    User=meshinfo
    Group=meshinfo
    Restart=no
    RuntimeDirectory=meshinfo
    WorkingDirectory=/opt/mesh-info/src
    ExecStart=/opt/mesh-info/bin/python -m meshinfo web --bind=unix:/run/mesh-info.sock

    [Install]
    WantedBy=multi-user.target

``/etc/systemd/system/meshinfo-collector.service``

.. code-block:: ini

    [Unit]
    Description=Mesh Info Collector Service
    After=network.target

    [Service]
    Type=simple
    User=meshinfo
    Group=meshinfo
    Restart=no
    RuntimeDirectory=meshinfo
    WorkingDirectory=/opt/mesh-info/src
    ExecStart=/opt/mesh-info/bin/python -m meshinfo collector

    [Install]
    WantedBy=multi-user.target

Run these commands to enable the services (so they run on future restarts)
and start them now.

.. code-block:: console

    $ sudo systemctl enable --now meshinfo-web.service
    $ sudo systemctl enable --now meshinfo-collector.service


NGINX Reverse Proxy
-------------------

It is generally recommended to run the Python Gunicorn process
(which is part of ``meshinfo web``)
behind a NGINX reverse proxy.

.. code-block:: console

    $ sudo apt install -y nginx-light

Create ``/etc/nginx/sites-available/mesh-info`` with the following content
(setting the ``server_name`` directive to whatever name(s) and/or IP(s) Mesh Info should be served on):

.. code-block:: nginx

    upstream app_server {
        # fail_timeout=0 means we always retry an upstream even if it failed
        # to return a good HTTP response

        # for UNIX domain socket setups
        server unix:/run/mesh-info.sock fail_timeout=0;
    }

    server {
        server_name YOUR.SERVER.NAME ANOTHER.SERVER.NAME;
        listen 8080;

        gzip on;
        gzip_min_length 10000;  # compress content over 10KB
        gzip_types application/json;
        gzip_proxied any;

        location / {
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Host $http_host;

            # we don't want nginx trying to do something clever with
            # redirects, we set the Host: header above already.
            proxy_redirect off;
            proxy_pass http://app_server;

            # TODO: have NGINX cache static content once cache busting is configured
        }
    }

Now enable the site, test the config, and then reload NGINX
(assuming no issues):

.. code-block:: console

    $ sudo ln -s /etc/nginx/sites-available/mesh-info /etc/nginx/sites-enabled/
    $ nginx -t
    $ sudo systemctl reload nginx

Now you can verify it is working by connecting to http://your.server.name:8080.

Upgrading
---------

To get the latest version of Mesh Info, run the following:

.. code-block:: console

    $ sudo systemctl stop meshinfo-web meshinfo-collector
    $ cd /opt/mesh-info/src
    $ sudo -u meshinfo git pull
    $ sudo -u meshinfo /opt/mesh-info/bin/alembic -c /opt/mesh-info/src/alembic.ini upgrade head
    $ sudo systemctl restart meshinfo-web meshinfo-collector

.. warning::

    Remember to check the the :doc:`changelog <changelog>` before upgrading in case there are impactful changes.

Troubleshooting
---------------

Tips for some common problems.

502 Bad Gateway
^^^^^^^^^^^^^^^

This means that the NGINX web server is running, but it cannot connect to Mesh Info.
To see what the Mesh Info web service is reporting, run ``sudo journalctl -u meshinfo-web``.
