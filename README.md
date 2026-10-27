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
python manage.py seed_demo                    # Usuarios admin/operador/cliente (@demo.test) y 3 productos
python manage.py identify_copy rutarchivo    # Recupera usuario y orden desde el fingerprint de una copia descargada
python manage.py test apps                    # Pruebas del flujo completo
```

### Apps y BD
```powershell
python manage.py startapp catalogo apps\catalogo # Crear una app dentro de apps/ ~ Cambiar dentro de apps.py el `name` a apps.catalogo ~ agregar al config como `apps.catalogo` a LOCAL_APPS en config/settings/base.py
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations
```

### Produccion
```powershell
pip install -r requirements.txt
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py check --deploy # Revision de seguridad
python manage.py migrate # Migra BD en RDS
python manage.py collectstatic --noinput # Estaticos al S3
sudo systemctl restart gunicorn # Reiniciar la app
sudo journalctl -u gunicorn -f # Para ver logs
```