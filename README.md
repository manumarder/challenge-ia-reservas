# Sistema local de reservas de laboratorio

## 1. Especificación breve

El laboratorio necesita consultar disponibilidad, reservar unidades físicas de un inventario fijo y cancelar sin perder el historial.

**Requisitos verificables:**

- Consultar disponibilidad y crear reservas para MIC-01, MIC-02, OSC-01, MUL-01 y FUE-01.
- Exigir solicitante no vacío, fechas con formato válido y un inicio anterior al fin.
- Rechazar superposiciones activas de la misma unidad; permitir intervalos consecutivos y unidades distintas en paralelo.
- Cancelar conservando ID y datos, liberar el intervalo y recuperar reservas activas y canceladas después de reiniciar.

Los intervalos son semiabiertos `[inicio, fin)`, por lo que 10:00-11:00 y 11:00-12:00 son consecutivos, no superpuestos. Las fechas usan `YYYY-MM-DDTHH:MM`, sin zona horaria explícita; se interpretan como hora local del laboratorio y todas las reservas deben usar la misma zona. Se aceptan fechas pasadas y no se impone duración máxima ni anticipación. No se administra el inventario ni se incluyen autenticación, notificaciones o concurrencia distribuida.

**Aceptación:** la suite debe comprobar creación, colisión, límites consecutivos, unidades distintas, entradas inválidas, cancelación e historial persistente tras reiniciar procesos.

## 2. Solución

`main.py` ofrece la CLI; `reservas.py` contiene reglas y persistencia JSON; `inventory.json` contiene el inventario fijo; `tests/` contiene pruebas automáticas. Solo se requiere Python 3.10 o superior; esta entrega se ejecutó con Python 3.12.10. No hay dependencias de terceros ni archivo de bloqueo porque se usa exclusivamente la biblioteca estándar.

Desde la raíz del repositorio:

```powershell
python --version
python -m unittest discover -s tests -v
python main.py inventory
python main.py availability MIC-01 2026-11-02T10:00 2026-11-02T11:00
python main.py reserve MIC-01 "Ada Lovelace" 2026-11-02T10:00 2026-11-02T11:00
python main.py reservations
python main.py cancel ID_DE_RESERVA
```

La salida es JSON. `reserve` devuelve el ID generado junto con unidad, solicitante, intervalo y estado; `availability` devuelve `available: true` o `false`. Se pueden usar distintos archivos de datos con `--data ruta.json`, por ejemplo para pruebas aisladas. Por defecto, los datos persisten en `data/reservations.json`. El directorio `data/` está excluido de Git para no publicar reservas locales. Borrar ese archivo reinicia y elimina el historial; no existe un comando de reinicio que borre datos accidentalmente. La prueba entre procesos usa un archivo temporal y no modifica los datos del usuario.

**Limitaciones:** almacenamiento local JSON sin bloqueo para escritores concurrentes; pensado para una instancia local. No se codifica una zona horaria ni se rechazan fechas pasadas.

## 3. Preparación del agente

- **Entorno:** VS Code con GitHub Copilot, actuando sobre el repositorio local mediante edición de archivos y ejecución real de comandos. La versión de VS Code no quedó registrada en el contexto disponible.
- **Modelo:** GitHub Copilot fue el agente utilizado; el identificador exacto del modelo no está visible en esta sesión y queda pendiente de completar desde la interfaz antes de entregar. No se inventa.
- **Instrucción y contexto:** se proporcionó la consigna PDF completa y el pedido de resolver el trabajo. El repositorio estaba vacío salvo por `.git`; no se suministraron reservas ni datos reales. La configuración de workspace `.vscode/settings.json` fija `python-envs.defaultEnvManager` en `ms-python.python:system`; se creó al configurar el intérprete Python del proyecto. No se añadió configuración externa ni instrucciones persistentes específicas del agente.
- **Herramientas y controles:** se permitió leer y modificar el repositorio y ejecutar Python en la terminal. No se usaron servicios externos. El agente ejecutó las pruebas documentadas abajo; la inspección y aceptación final de los cambios por Manuela está pendiente. Las salidas automáticas no se presentan como revisión humana.
- **Adaptación comprobable:** para probar persistencia, se convirtió “recuperar al reiniciar” en una prueba que lanza procesos CLI separados para crear, cancelar y volver a listar registros. El progreso y las decisiones se conservan en este README y el procedimiento está implementado en `tests/test_reservas.py`.

## 4. Registro de decisiones y delegación

### Decisiones

- Se eligió Python estándar y JSON para que instalación y ejecución sean locales y reproducibles sin cuenta del modelo ni dependencias de terceros. SQLite sería más apropiado con varios escritores, pero no se requiere concurrencia distribuida.
- Se fijó el intervalo semiabierto `[inicio, fin)` y fechas locales sin zona horaria para definir inequívocamente los bordes consecutivos. Pasado y duración quedan sin restricciones porque la consigna no las impone.
- Se conserva cada reserva y se cambia su estado a `cancelled`; no se borra el registro.

### Episodio 1: disponibilidad y superposición

- **Objetivo/requisito:** evitar dos reservas activas superpuestas de una misma unidad y permitir límites consecutivos.
- **Contexto e instrucción:** consigna, “Rechazar superposiciones de reservas activas de la misma unidad. Permitir límites consecutivos y reservas simultáneas de unidades distintas.” Se pidió resolver las reglas de reserva en el repositorio local.
- **Acción del agente:** implementó validación de intervalo en `reservas.py` y pruebas para colisión, consecutividad y unidades distintas.
- **Decisión humana:** revisión y aceptación por Manuela pendientes; no se atribuye una corrección ni aprobación que no ocurrió.
- **Evidencia:** `reservas.py`; `tests/test_reservas.py`; ejecución de `python -m unittest discover -s tests -v` registrada abajo.

### Episodio 2: cancelación con historial

- **Objetivo/requisito:** cancelar sin perder ID ni datos y liberar disponibilidad.
- **Contexto e instrucción:** consigna, “Cancelar conservando identificador y datos, y liberar el intervalo.”
- **Acción del agente:** implementó el estado `cancelled`; la disponibilidad ignora reservas canceladas y el registro queda almacenado.
- **Decisión humana:** revisión y aceptación por Manuela pendientes.
- **Evidencia:** `reservas.py`; prueba `test_cancellation_keeps_record_and_releases_interval` en `tests/test_reservas.py`.

### Episodio 3: persistencia y recuperación

- **Objetivo/requisito:** conservar reservas activas y canceladas al detener y reiniciar la aplicación.
- **Contexto e instrucción:** consigna, “Persistir reservas y estados para recuperarlos al reiniciar la aplicación.”
- **Acción del agente:** implementó almacenamiento JSON y una prueba de integración que crea, cancela y lista desde procesos CLI independientes.
- **Decisión humana:** revisión y aceptación por Manuela pendientes.
- **Evidencia:** `reservas.py`; `main.py`; prueba `test_active_and_cancelled_reservations_survive_process_restart` en `tests/test_reservas.py`.

### Verificación registrada

La ejecutó el agente en este entorno; no equivale a una verificación humana independiente.

| Comando | Resultado observado |
| --- | --- |
| `C:/Users/manu/AppData/Local/Microsoft/WindowsApps/python3.12.exe -m unittest discover -s tests -v` | Python 3.12.10; 9 pruebas, `OK`, incluida persistencia entre procesos |

La suite usa fechas fijas de noviembre de 2026 para que no dependa de la fecha actual. El resultado es del agente en este entorno; Manuela aún debe revisar y aceptar la implementación para completar la verificación humana solicitada.