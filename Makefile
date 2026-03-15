serve:
	python manage.py runserver

flush:
	python manage.py flush

seed:
	python manage.py seed

migrate:
	python manage.py makemigrations ally
	python manage.py migrate