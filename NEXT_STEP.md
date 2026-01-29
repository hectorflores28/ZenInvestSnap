### **1. Implementar el Sistema de Usuarios y Multi-tenencia**

- **Modificar el Modelo:** Añadir  a los modelos de **Asset**, **Transaction** y **PortfolioValue**.
    
    ```
    user = models.ForeignKey(User, ...)
    ```
    
- **Vistas de Auth:** Crear las páginas de **Registro** y **Login** con una estética premium coherente con lo que ya tienes.
- **Protección:** Asegurar que el Dashboard solo muestre los datos del usuario logueado.

### **2. Convertir las Apps en Controladores Reales**

- Cada app (, , etc.) debería tener una vista simple para que el usuario pueda:
    
    ```
    bitso
    ```
    
    ```
    gbm
    ```
    
    - Ver el estado de la conexión.
    - Ingresar sus credenciales (encriptadas) o saldos manuales.
    - Ver el detalle específico de esa fuente.

### **3. Panel de Gestión de Transacciones**

- Necesitas un lugar para registrar compras/ventas manuales (especialmente para "Otros" activos o cuando la API falla). Sin esto, no puedes calcular el  de forma precisa.
    
    ```
    total_invested
    ```

### **4. Dashboard Dinámico y Pro**

- Añadir gráficos (Chart.js) para ver la evolución del portafolio.
- Botón de "Sincronizar ahora" que dispare la lógica de las APIs en tiempo real.