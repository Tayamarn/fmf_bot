#!/bin/bash
apt-get install -y sqlite python python-pip python-virtualenv supervisor git
LOG_DIR=/var/log/fmf_bot
if [ ! -d "$LOG_DIR" ]
then
    mkdir -p "$LOG_DIR"
fi
WORKDIR=/usr/share/fmf_bot
if [ ! -d "$WORKDIR" ]
then
    mkdir "$WORKDIR"
    git clone https://github.com/Tayamarn/fmf_bot.git $WORKDIR
    virtualenv $WORKDIR/venv
    source $HOMEPAGE_WORK_DIR/venv/bin/activate
    pip install telepot
    deactivate
fi

cp ${WORKDIR%/*}/supervisor.conf /etc/supervisor/conf.d/fmf_bot.conf
supervisorctl reload
supervisorctl restart fmf_bot
