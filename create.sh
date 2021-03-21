#!/bin/bash
apt-get update
apt-get install -y sqlite python3 python3-pip python3-virtualenv supervisor git
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
    source $WORKDIR/venv/bin/activate
    pip install aiogram
    deactivate
fi

cp ${WORKDIR}/supervisor.conf /etc/supervisor/conf.d/fmf_bot.conf
supervisorctl reload
supervisorctl restart fmf_bot
