python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

touch .env

nano .env

python manage.py makemigrations

python manage.py migrate

python manage.py createsuperuser

python manage.py loaddata initial_assets.json

python manage.py fetch_prices
python manage.py calculate_values
python manage.py update_portfolio
python manage.py runserver