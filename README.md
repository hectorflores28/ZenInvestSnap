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

El sistema se basa en cuatro modelos clave: `Asset`, `Transaction`, `DailySnapshot` (el precio diario de cada activo), y `PortfolioValue` (el resumen diario del portafolio).

La rutina diaria se ejecuta con un único comando para garantizar la atomicidad de los datos:
```bash
python manage.py run_daily_snapshot
```

## 🤝 Contribución

¡Las contribuciones son bienvenidas\! Si deseas mejorar la precisión de los cálculos, integrar nuevas APIs financieras o proponer mejoras al Dashboard, sigue los siguientes pasos:

1.  Haz *fork* del repositorio.
2.  Crea una rama para tu *feature* (`git checkout -b feature/nombre-de-tu-feature`).
3.  *Commit* tus cambios (`git commit -m 'feat: Descripción breve del cambio'`).
4.  *Push* a la rama (`git push origin feature/nombre-de-tu-feature`).
5.  Abre un **Pull Request**.

## 📝 Licencia

Este proyecto está bajo la Licencia MIT.