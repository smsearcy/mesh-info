Installation
============

Mesh Info requires Python 3.9+ and RRDtool libraries.
The following instructions include installing those dependencies.

Installation instructions for Raspberry Pi OS
(tested on Bullseye).
This will create a ``meshinfo`` user,
install the application to ``/opt/mesh-info`` as that user
(in a Python virtualenv),
and create ``/var/lib/mesh-info`` for storing the application data.

.. note::

    If you are interested in setting up Mesh Info for development,
    please see :doc:`contributing`.

.. code-block:: console

    sudo apt update
    sudo apt install -y git librrd-dev python3 python3-dev python3-pip python3-venv rrdtool
    sudo useradd meshinfo
    sudo mkdir /opt/mesh-info /var/lib/mesh-info
    sudo chown meshinfo: /opt/mesh-info /var/lib/mesh-info
    sudo -u meshinfo git clone https://github.com/smsearcy/mesh-info.git /opt/mesh-info/src
    sudo -u meshinfo python3 -m venv /opt/mesh-info/
    sudo -u meshinfo /opt/mesh-info/bin/pip install -U pip wheel
    cd /opt/mesh-info/src
    sudo -u meshinfo /opt/mesh-info/bin/pip install -r requirements.txt -e .
    sudo -u meshinfo /opt/mesh-info/bin/alembic upgrade head

To run a test scan,
you can run the following
(optionally specifying the name or IP of the local node,
in case ``localnode.local.mesh`` does not resolve):

.. code-block:: console

    /opt/mesh-info/bin/meshinfo report [LOCAL_NODE]

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

    /opt/mesh-info/bin/meshinfo collector --run-once

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

    sudo systemctl enable --now meshinfo-web.service meshinfo-collector.service


NGINX Reverse Proxy
-------------------

It is generally recommended to run the Python Gunicorn process
(which is part of ``meshinfo web``)
behind a NGINX reverse proxy.

.. code-block:: console

    sudo apt install -y nginx-light

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

        # reverse proxy the Gunicorn app server
        location / {
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Host $http_host;

            # we don't want nginx trying to do something clever with
            # redirects, we set the Host: header above already.
            proxy_redirect off;
            proxy_pass http://app_server;
        }

        # server static files via NGINX
        location /static {
            root /opt/mesh-info/src/meshinfo;
        }
    }

Now enable the site, test the config, and then reload NGINX
(assuming no issues):

.. code-block:: console

    sudo ln -s /etc/nginx/sites-available/mesh-info /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl reload nginx

Now you can verify it is working by connecting to http://your.server.name:8080.

Upgrading
---------

To get the latest version of Mesh Info, run the following:

.. code-block:: console

    sudo systemctl stop meshinfo-web meshinfo-collector
    cd /opt/mesh-info/src
    sudo -u meshinfo git pull
    sudo -u meshinfo /opt/mesh-info/bin/pip install -r requirements.txt
    sudo -u meshinfo /opt/mesh-info/bin/alembic upgrade head
    sudo systemctl restart meshinfo-web meshinfo-collector

.. warning::

    Remember to check the the :doc:`changelog <changelog>` before upgrading in case there are impactful changes.

Troubleshooting
---------------

Tips for some common problems.

502 Bad Gateway
^^^^^^^^^^^^^^^

This means that the NGINX web server is running, but it cannot connect to Mesh Info.
To see what the Mesh Info web service is reporting, run ``sudo journalctl -u meshinfo-web``.
