#!/bin/sh

# Wait for Database image to start
if [ "$DATABASE" = "postgres" ]
then
	echo "Waiting for postgres..."

	while ! nc -z $SQL_HOST $SQL_PORT; do
		sleep 0.1
	done

	echo "PostgreSQL started"
fi

# Run django migrations and collect static
echo "Collect static files"
python3 manage.py collectstatic --noinput

echo "Make database migrations"
python3 manage.py makemigrations

echo "Apply database migrations"
python3 manage.py migrate

exec "$@"