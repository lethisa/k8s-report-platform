#!/bin/sh

python -m scripts.wait_for_db

flask db upgrade

python -m scripts.bootstrap_admin

exec gunicorn \
    -b 0.0.0.0:5000 \
    run:app