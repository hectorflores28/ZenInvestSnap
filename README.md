# 📈 ZenInvestSnap: Seguimiento de Inversiones Automatizado con Django

zen-invest-snap (directorio proyecto)
.env
README.md
requirements.txt

>

main (directorio app)
- Layouts (base.html, dashboard.html, login.html, register.html)
- Models (asset.py, daily_snapshot.py, portfolio_value.py, transaction.py)
- Views (dashboard.py, login.py, register.py)
- URLs (urls.py)
- Logic (calculations.py)
- run_daily_snapshot.py
zen_invest_snap (directorio app)
- providers.py
bitso (directorio app)
- provider.py
gbm (directorio app)
mercado_pago (directorio app)
nu (directorio app)

## 🚀 Instalación y Configuración

### 1. Preparación del Entorno (Local)
```bash
# Crear entorno virtual
python -m venv venv
# Activar (Windows)
venv\Scripts\activate
# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración de Variables de Entorno
Crea un archivo `.env` en la raíz basado en `.env.example`:
```env
DEBUG=True
SECRET_KEY=tu_clave_secreta
BITSO_API_KEY=tu_key
BITSO_API_SECRET=tu_secret
... (ver .env.example para más variables)
```

### 3. Docker (Recomendado 🚀)
Si tienes Docker y Docker Compose instalados, puedes levantar el proyecto fácilmente:

1.  **Levantar el servicio:**
    ```bash
    docker-compose up -d --build
    ```
2.  **Primera inicialización (si quieres crear un superusuario):**
    ```bash
    docker-compose exec web python zen_invest_snap/manage.py createsuperuser
    ```
    La aplicación ejecuta `migrate` automáticamente al arrancar, así que no necesitas crear la base de datos manualmente antes del primer acceso.
3.  **Acceder:** Visita `http://localhost:8000` en tu navegador.

### 4. Base de Datos (Local)
Si prefieres correrlo localmente sin Docker:
```bash
cd zen_invest_snap
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Moneda y sincronización del portafolio
- Los precios de las transacciones se capturan en MXN. El dashboard muestra MXN por defecto y el botón **Ver en USD** convierte temporalmente los valores usando el último tipo de cambio USD/MXN disponible en internet.
- Si no se puede consultar el tipo de cambio, el dashboard muestra un error y mantiene los montos en MXN.
- **Sync Portafolio** consulta los saldos de Bitso (si están configuradas sus llaves), obtiene precios de acciones, ETF y cripto con Yahoo Finance, convierte cotizaciones USD a MXN y guarda snapshots diarios y el total del portafolio. Los tickers mexicanos deben usar el sufijo `.MX` para reconocer cotizaciones en pesos.
- Al no poder consultar el tipo de cambio durante la sincronización, se conserva el último precio guardado en MXN cuando existe. Los precios USD antiguos quedan pendientes hasta una sincronización exitosa; los valores históricos anteriores a la normalización no se incluyen en la gráfica. GBM, Nu y Mercado Pago aún no tienen sincronización automática implementada.
- Precisión de datos: `Transaction.price` y `DailySnapshot.closing_price` guardan hasta 4 decimales; las cantidades guardan hasta 10; los totales diarios de `PortfolioValue` guardan 2. El dashboard también calcula el total actual desde posiciones y snapshots, y lo presenta redondeado a 2 decimales sin reducir la precisión de los cálculos ni modificar esos campos.

## 🔮 Próximos Pasos (Hoja de Ruta)
1.  **Integraciones Pendientes:** Completar los proveedores para GBM, Nu y Mercado Pago.
2.  **Credenciales por Usuario:** Implementar un sistema para que cada usuario guarde sus propias llaves API encriptadas en la base de datos, en lugar de usar variables de entorno globales.
3.  **Alertas:** Sistema de notificaciones cuando un activo sube o baja de cierto porcentaje.

## 🤝 Contribución
¡Las contribuciones son bienvenidas! Sigue el flujo estándar de Pull Requests.

## 📄 Licencia
Este proyecto está bajo la Licencia MIT - mira el archivo [LICENSE](LICENSE) para detalles.
