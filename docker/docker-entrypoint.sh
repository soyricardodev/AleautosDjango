#!/bin/bash
set -e

ENV_FILE_PATH=.env

if [ -e .env ]
then
    echo "the .env file exist, pulling from the file"
else
    echo "the .env file do not exist, pulling from the environment variables"
fi

#if environmet variable APP_ENV is equal to production then run the following commands
# makemigrations
python3.11 manage.py makemigrations 
# run migrate
python3.11 manage.py migrate
# Add crontab file in the cron directory
python3.11 manage.py crontab add 
# Start cron service
service cron start

echo "Environment: $DEBUG"
if [ "$DEBUG" = "True" ]
then
    echo "DEBUG mode activated"
    # Start development server
    python3.11 manage.py runserver 0.0.0.0:8000
else
    echo "DEBUG mode deactivated"
    # Start Supervisor
    supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
fi



