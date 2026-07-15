serve:
	python manage.py runserver 192.168.1.61:8000

flush:
	python manage.py flush

seed:
	python manage.py seed

migrate:
	python manage.py makemigrations 
	python manage.py migrate