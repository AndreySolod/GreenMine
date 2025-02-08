#!/bin/bash

_term() {
  echo "Caught SIGINT signal, stopping the server!"
  kill -SIGINT "$child"
  wait "$child"
}
trap _term SIGINT
trap _term SIGTERM

echo "upgradig existing database"
flask db upgrade
echo "Loading unexist database value from default_database_value.yml file"
flask greenmine-command update-database-value
echo "now we can run application"
gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker --bind 0.0.0.0:5000 -w 1 'GreenMine:create_gunicorn_app()' &
child=$!
wait "$child"
