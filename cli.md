### 1\. Preparación del Entorno


```bash
# Crear el entorno virtual
python -m venv venv

# ACTIVACIÓN DEL ENTORNO VIRTUAL
# ------------------------------------
# Si usas Linux/macOS/Git Bash/WSL:
source venv/bin/activate
# Si usas Windows Command Prompt (cmd):
# venv\Scripts\activate
# Si usas Windows PowerShell:
# venv\Scripts\Activate.ps1
# ------------------------------------

# Instalar dependencias (asumiendo que 'requirements.txt' existe en la raíz)
pip install -r requirements.txt

# Crear el archivo de variables de entorno (para secretos/API Keys)
touch .env

# Abrir el editor para configurar las variables de entorno (ej. API_KEY=...)
nano .env 
# o 'code .env' si usas VS Code
```

### 2\. Configuración Inicial de Django

```bash
# Crear migraciones iniciales de los modelos
python manage.py makemigrations

# Aplicar las migraciones a la base de datos
python manage.py migrate

# Crear un usuario administrador
python manage.py createsuperuser

# Cargar los activos iniciales (tickers) si el archivo existe
python manage.py loaddata initial_assets.json
```

### 3\. Rutina de Ejecución Diaria y Servidor

```bash
# ------------------------------------
# EJECUCIÓN DIARIA (El cron job usará este comando)
# Este comando ejecuta: fetch_prices -> calculate_values -> update_portfolio
python manage.py run_daily_snapshot
# ------------------------------------

# Iniciar el servidor de desarrollo de Django
python manage.py runserver
```