# eCommerce-contenido-digital

## Desarrollo local

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements/local.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

## Variables de entorno

Ver [.env.example](.env.example). En producción se definen en `/etc/ecommerce/ecommerce.env` en EC2.

## Comandos comunes
### Entorno de trabajo
```powershell
python -m venv venv -- Si no existe aun
venv\Scripts\activate
pip install -r requirements/local.txt
pip freeze
copy .env.example .env
```
### App
```powershell
python manage.py runserver
python manage.py check
python manage.py createsuperuser
python manage.py shell
```
### Datos de prueba y utilidades
```powershell
python manage.py seed_demo                    # Admin/operator/client users (@demo.test) and 3 products
python manage.py identify_copy path/to/file # Recover user and order from the fingerprint of a downloaded copy
python manage.py test apps                    # Full purchase flow tests
```

### Apps y BD
```powershell
python manage.py startapp catalogo apps\catalogo # Create an app inside apps/ ~ In apps.py change `name` to apps.catalogo ~ add `apps.catalogo` to LOCAL_APPS in config/settings/base.py
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations
```

### Produccion
```powershell
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py check --deploy # Security check
python manage.py migrate # Migrate the RDS database
python manage.py collectstatic --noinput # Static files to S3
sudo systemctl restart gunicorn # Restart the app
sudo journalctl -u gunicorn -f # Follow the logs
```