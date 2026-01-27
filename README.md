# 📈 ZenInvestSnap: Seguimiento de Inversiones Automatizado con Django

## Descripción
ZenInvestSnap es un sistema de seguimiento de portafolio de inversiones diseñado para ofrecer una visión diaria, clara y sin estrés (Zen) del estado de tus activos financieros. Utilizando la potencia de **Django** y **Python**, el proyecto automatiza la captura de precios de mercado y el cálculo de la rentabilidad diaria.

## ✨ Enfoque y Metas del Proyecto

### Enfoque
El enfoque principal es la **automatización** y la **claridad de los datos**. En lugar de depender de hojas de cálculo o cálculos manuales, ZenInvestSnap utiliza un **Django Management Command** que se ejecuta diariamente (via `cron`) para asegurar que todos los datos y métricas estén actualizados y listos para su visualización.

### Metas Clave
1. **Snapshots Diarios Confiables:** Registrar el precio de cierre de cada activo y el valor total del portafolio al final del día.
2. **Visualización de Rentabilidad:** Mostrar claramente la métrica clave: la comparación del **Valor de Mercado Actual** frente al **Valor Total Invertido** (con un indicador visual Semáforo).
3. **Mantenimiento Simple:** Usar la estructura robusta de Django (Modelos, ORM, Management Commands) para un sistema escalable y de bajo mantenimiento.

## 🛠️ Estructura Técnica

El proyecto está organizado en varias aplicaciones Django para modularidad:

- **main**: Contiene los modelos núcleo (`Asset`, `Transaction`, `DailySnapshot`, `PortfolioValue`) y la lógica central.
- **gbm**: Integración para obtener datos de GBM.
- **mercado_pago**: Integración para Mercado Pago.
- **nu**: Integración para Nu.
- **bitso**: Integración para Bitso.

### Modelos Principales
El sistema se basa en cuatro modelos clave (definidos en `main/models.py`):
- `Asset`: Representa un activo financiero (Stock, Crypto, Fiat, etc.).
- `Transaction`: Registra compras, ventas, depósitos y retiros.
- `DailySnapshot`: Almacena el precio de cierre diario de cada activo.
- `PortfolioValue`: Resumen diario del valor total del portafolio e inversión total.

### Automatización
La rutina diaria se ejecuta con un único comando:
```bash
python manage.py run_daily_snapshot
```
Este comando se encarga de:
1. Obtener precios actuales de las diferentes fuentes (APIs).
2. Guardar el snapshot de cada activo.
3. Calcular y guardar el valor total del portafolio.

## 🚀 Instalación y Configuración

### 1. Preparación del Entorno

Clona el repositorio y navega al directorio del proyecto.

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración de Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto para tus credenciales y configuración:

```bash
touch .env
```
Agrega tus claves API y configuración de base de datos en el archivo `.env`.

### 3. Configuración de Django

Realiza las migraciones iniciales para crear la estructura de base de datos:

```bash
cd zen_invest_snap
python manage.py makemigrations
python manage.py migrate

# Crear superusuario para administrar el sitio
python manage.py createsuperuser
```

## 🤝 Contribución

¡Las contribuciones son bienvenidas! Si deseas mejorar la precisión de los cálculos, integrar nuevas APIs financieras o proponer mejoras al Dashboard, sigue los siguientes pasos:

1.  Haz *fork* del repositorio.
2.  Crea una rama para tu *feature* (`git checkout -b feature/nombre-de-tu-feature`).
3.  *Commit* tus cambios (`git commit -m 'feat: Descripción breve del cambio'`).
4.  *Push* a la rama (`git push origin feature/nombre-de-tu-feature`).
5.  Abre un **Pull Request**.

## 📝 Licencia

Este proyecto está bajo la Licencia MIT.