.PHONY: run-db stop-db clean-db

serve:
	python manage.py runserver 192.168.1.61:8000

flush:
	python manage.py flush

seed:
	python manage.py seed

migrate:
	python manage.py makemigrations
	python manage.py migrate


DB_NAME = ally_dev_postgis_container

start-db:
	docker start $(DB_NAME)

run-db:
	docker run --name $(DB_NAME) \
	  -e POSTGRES_DB=gis_db \
	  -e POSTGRES_USER=gis_user \
	  -e POSTGRES_PASSWORD=gis_pass \
	  -p 5432:5432 \
	  -d postgis/postgis

stop-db:
	docker stop $(DB_NAME)

clean-db: stop-db
	docker rm $(DB_NAME)
