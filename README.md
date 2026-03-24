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

# de aqui para abajo limpiar (despues)

# Necesito ver si hay api's diponibles, si no dejo todo local

## Descripción
ZenInvestSnap es un sistema de seguimiento de portafolio de inversiones diseñado para ofrecer una visión diaria, clara y sin estrés (Zen) del estado de tus activos financieros. Utilizando la potencia de **Django** y **Python**, el proyecto automatiza la captura de precios de mercado y el cálculo de la rentabilidad diaria.

## ✨ Enfoque y Metas del Proyecto

### Enfoque
El enfoque principal es la **automatización** y la **claridad de los datos**. En lugar de depender de hojas de cálculo o cálculos manuales, ZenInvestSnap permite sincronizar tus activos directamente desde APIs (como Bitso) o registrarlos manualmente, asegurando que todos los datos y métricas estén actualizados.

### Funcionalidades Logradas
1.  **Snapshots Diarios Confiables:** Registro automático del precio de cierre de cada activo y el valor total del portafolio.
2.  **Dashboard Premium:** Visualización clara del valor de mercado vs. inversión total con indicadores visuales de rentabilidad y gráficas históricas (Chart.js).
3.  **Sistema Multi-usuario:** Registro, inicio de sesión y protección de datos por usuario. Cada usuario tiene su propio portafolio.
4.  **Sincronización en Tiempo Real:** Botón "Sync Portafolio" que dispara la actualización de precios y saldos desde la interfaz web.
5.  **Gestión de Transacciones:** Formulario para registrar compras, ventas, depósitos y retiros manualmente.

## 🛠️ Estructura Técnica

El proyecto está organizado en varias aplicaciones Django para modularidad:

-   **main**: Contiene los modelos núcleo (`Asset`, `Transaction`, `DailySnapshot`, `PortfolioValue`), la lógica de cálculo y el dashboard principal.
-   **bitso**: Integración funcional para obtener saldos y precios desde Bitso Exchange.
-   **gbm / mercado_pago / nu**: Estructuras modulares preparadas para futuras integraciones.

### Modelos Principales
-   `Asset`: Representa un activo financiero (Stock, Crypto, Fiat, etc.).
-   `Transaction`: Registra compras, ventas, depósitos y retiros para calcular el costo promedio.
-   `DailySnapshot`: Almacena el precio de cierre diario de cada activo.
-   `PortfolioValue`: Resumen diario del valor total por usuario.

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
2.  **Preparar la base de datos (solo la primera vez):**
    ```bash
    docker-compose exec web python zen_invest_snap/manage.py migrate
    docker-compose exec web python zen_invest_snap/manage.py createsuperuser
    ```
3.  **Acceder:** Visita `http://localhost:8000` en tu navegador.

### 4. Base de Datos (Local)
Si prefieres correrlo localmente sin Docker:
```bash
cd zen_invest_snap
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## 🔮 Próximos Pasos (Hoja de Ruta)
1.  **Integraciones Pendientes:** Completar los proveedores para GBM, Nu y Mercado Pago.
2.  **Credenciales por Usuario:** Implementar un sistema para que cada usuario guarde sus propias llaves API encriptadas en la base de datos, en lugar de usar variables de entorno globales.
3.  **Alertas:** Sistema de notificaciones cuando un activo sube o baja de cierto porcentaje.

## 🤝 Contribución
¡Las contribuciones son bienvenidas! Sigue el flujo estándar de Pull Requests.

## 📝 Licencia
Este proyecto está bajo la Licencia MIT.