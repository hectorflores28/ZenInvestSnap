1. **Falta de Identidad y Seguridad:** El sistema está diseñado actualmente para un solo usuario global. No hay modelos de  vinculados a los activos, ni vistas de  o . Cualquier persona que entre a la IP ve todo.
    
    ```
    User
    ```
    
    ```
    Login
    ```
    
    ```
    Registro
    ```
    
2. **Apps "Huérfanas":** Tienes las carpetas para , , , etc., pero están vacías o solo tienen lógica de backend (**provider.py**). No funcionan como "módulos" independientes con sus propios controladores o interfaces.
    
    ```
    gbm
    ```
    
    ```
    bitso
    ```
    
    ```
    nu
    ```
    
3. **Lógica Centralizada en Management Commands:** Todo depende de que corras un comando manual. No hay una manera desde la web de "Sincronizar ahora" o de configurar tus llaves API de forma segura por usuario.