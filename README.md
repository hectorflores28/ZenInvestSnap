# ZenInvestSnap
¡Excelente idea de proyecto\! Dada tu experiencia en **Django** y tu interés en el análisis de datos (como se ve en tu proyecto `django-strava-analytics-dashboard`), un sistema de seguimiento de inversiones automatizado es un ajuste perfecto.

Aquí tienes una propuesta de nombre y una estructura técnica detallada para tu proyecto.

## 💡 Idea de Nombre para el Proyecto

Busco un nombre que sea profesional, que refleje el aspecto financiero (Zen/Finanzas) y el toque tecnológico (Datos/Automatización).

  * **ZenInvestSnap**
      * Combina **Zen** (calma, control), **Invest** (inversión) y **Snap** (por "snapshot" diario). Sugiere una visión clara y sin estrés de tus finanzas.
  * **AuraFinance**
      * "Aura" sugiere una visión completa y un resumen del estado de tus inversiones.
  * **PyPortfolio**
      * Simple, directo y resalta el uso de **Python** para gestionar tu **Portafolio**.

-----

## 🏗️ Estructura y Componentes Clave del Proyecto Django

Tu enfoque de **cron** y **scripts de pasos secuenciales** es perfecto para este tipo de proyecto.

### 1\. Modelos de Base de Datos (Django Models)

Necesitarás modelos para rastrear tus activos, las transacciones que realizaste, y los valores diarios.

| Modelo | Descripción | Campos Clave |
| :--- | :--- | :--- |
| **Asset** | El activo financiero (ej. GOOGL, S\&P 500 ETF, CETE). | `ticker` (clave), `name`, `type` (Acción, ETF, Cripto, etc.). |
| **Transaction** | Registro de cuándo y cuánto invertiste. | `asset` (FK), `date`, `type` (Compra/Venta), `shares`, `price_per_share`, `total_amount`. |
| **DailySnapshot** | **El corazón del proyecto.** Captura el valor del activo un día concreto. | `asset` (FK), `date`, `current_price`, `value_at_close`. |
| **PortfolioValue** | Registro global de tu portafolio en un día. | `date`, `total_invested`, `current_market_value`, `daily_profit_loss`, `overall_profit_loss`. |

-----

### 2\. La Rutina de Ejecución Diaria (`cron` / `run_all.py`)

En lugar de múltiples archivos `.py` ejecutados por un script externo (`run_all.py`), en Django, el método más robusto es usar un **Django Management Command**. Esto te da acceso directo al entorno de Django, a los modelos y al ORM.

#### A. Management Command (`management/commands/run_daily_snapshot.py`)

Este será el único script que tu `cron` llamará:

```bash
python manage.py run_daily_snapshot
```

#### B. La Lógica Secuencial Interna

El Management Command puede encapsular tus "steps" en una secuencia lógica:

| Archivo / Clase | Tu "Step" | Función |
| :--- | :--- | :--- |
| `step1_fetch_data.py` | **`step1.py`...** | **Obtención de Datos:** Llama a APIs de finanzas (Yahoo Finance, Alpha Vantage, etc.) para obtener el precio de cierre (`current_price`) de *todos* los **Assets** en tu portafolio. Guarda estos datos en la tabla **DailySnapshot**. |
| `step2_calculate_value.py` | **`stepN.py`...** | **Cálculo de Valor:** Para cada **Asset**, calcula el **Valor Actual Total** basándose en: (Acciones que poseo hoy) $\times$ (Precio de cierre de hoy). |
| `step3_update_portfolio.py` | **`stepN.py`...** | **Consolidación del Portafolio:** Suma todos los valores individuales de los activos para obtener el `current_market_value` global del día. Calcula el `overall_profit_loss` y guarda el registro en **PortfolioValue**. |

-----

### 3\. La Interfaz de Usuario (Dashboard)

El dashboard debe mostrar la comparación del valor actual vs. el valor invertido, como solicitas.

#### A. Vistas Clave

  * **Vista de Resumen General:** Muestra el registro más reciente de **PortfolioValue**.
      * **Métricas:** `Valor Invertido Total`, `Valor de Mercado Actual`, `Ganancia/Pérdida Total` ($ y %).
      * **Semáforo:** Un indicador grande que refleja el `overall_profit_loss`:
          * **Verde:** Ganancia (Valor Actual \> Valor Invertido).
          * **Rojo:** Pérdida (Valor Actual \< Valor Invertido).
          * **Amarillo:** Cerca de cero (Pérdida/Ganancia menor a $\pm$X%).
  * **Vista Detalle por Activo:** Para cada **Asset**, muestra la información clave:
      * **Precio invertido (promedio):** El costo promedio de todas tus transacciones de compra.
      * **Precio actual (snapshot):** El precio del **DailySnapshot** de hoy.
      * **Ganancia/Pérdida Individual:** La diferencia marcada con rojo/verde.
  * **Vista de Transacciones (Registros Aislados):** Una tabla simple que lista todos los registros de la tabla **Transaction** (compras/ventas) aislados.

