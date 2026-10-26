# Sistema local de reservas de laboratorio

## 1. Especificación breve

El laboratorio necesita consultar disponibilidad, reservar unidades físicas de un inventario fijo y cancelar sin perder el historial.

**Requisitos verificables:**

- Consultar disponibilidad y crear reservas para MIC-01, MIC-02, OSC-01, MUL-01 y FUE-01.
- Exigir solicitante no vacío, fechas con formato válido y un inicio anterior al fin.
- Rechazar superposiciones activas de la misma unidad; permitir intervalos consecutivos y unidades distintas en paralelo.
- Cancelar conservando ID y datos, liberar el intervalo y recuperar reservas activas y canceladas después de reiniciar.

Los intervalos son semiabiertos `[inicio, fin)`, por lo que 10:00-11:00 y 11:00-12:00 sąn consecutivos, no superpuestos. Las fechas usan `YYYY-MM-DDTHH:MM`, sin zona horaria explícita; se interpretan como hora local del laboratorio y todas las reservas deben usar la misma zona. Se aceptan fechas pasadas y no se impone duración máxima ni anticipación. No se administra el inventario ni se incluyen autenticación, notificaciones o concurrencia distribuida.

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

La salida es JSON. reserve devuelve el ID generado junto con unidad, solicitante, intervalo y estado; availability devuelve available: true o false. Se pueden usar distintos archivos de datos con --data ruta.json, por ejemplo para pruebas aisladas. Por defecto, los datos persisten en data/reservations.json. El directorio data/ está excluido de Git para no publicar reservas locales. Borrar ese archivo reinicia y elimina el historial; no existe un comando de reinicio que borre datos accidentalmente. La prueba entre procesos usa un archivo temporal y no modifica mis datos de usuario.

**Limitaciones:** almacenamiento local JSON sin bloqueo para escritores concurrentes; pensado para una instancia local. No se codifica una zona horaria ni se rechazan fechas pasadas.

## 3. Preparación del agente

- **Entorno:** Usé VS Code junto con GitHub Copilot, interactuando sobre el repositorio local mediante edición de archivos y ejecución directa de comandos en la terminal.
- **Modelo:** GitHub Copilot en VS Code, operando con el modelo GPT-6 Luna.
- **Instrucción y contexto:** Le proporcioné al agente la consigna completa del trabajo con el requerimiento de desarrollar el sistema de reservas completo desde cero en Python, incluyendo las reglas de negocio (inventario fijo, validación de superposiciones, turnos consecutivos y persistencia en JSON) junto con la suite de pruebas automáticas con `pytest` o `unittest`. Partí de un repositorio vacío, sin datos previos ni configuraciones externas añadidas.
- **Herramientas y controles:** Otorgué permisos para leer, modificar archivos del repositorio y ejecutar Python en la terminal local, sin recurrir a servicios externos. El agente ejecutó la suite inicial; posteriormente, verifiqué personalmente ejecutando la suite de pruebas y los comandos principales de la CLI, revisando los resultados y aceptando el comportamiento obtenido.
- **Adaptación comprobable:** Para validar la persistencia, diseñé junto con el agente una prueba automatizada que lanza procesos CLI separados para crear, cancelar y listar registros simulando reinicios. El progreso quedó registrado en este repositorio y en el script tests/test_reservas.py.

## 4. Registro de decisiones y delegación

### Decisiones

- Elegí Python estándar y JSON para que la instalación y ejecución sean locales y totalmente reproducibles, sin depender de cuentas del modelo ni librerías externas complejas. SQLite habría sido una alternativa con múltiples escritores, pero este escenario no requiere concurrencia distribuida.
- Fijé el intervalo semiabierto `[inicio, fin)` y fechas locales sin zona horaria para definir con precisión los bordes consecutivos. Las fechas pasadas y la duración quedaron sin restricciones estrictas porque la consigna no las exigía.
- Opté por una cancelación lógica: cada reserva se conserva en el historial cambiando su estado a `cancelled`, evitando borrar registros físicos.

### Episodio 1: disponibilidad y superposición

- **Objetivo/requisito:** Evitar dos reservas activas superpuestas para una misma unidad y permitir límites consecutivos.
- **Contexto e instrucción:** Indiqué al agente que implementara las reglas de validación de intervalos según la consigna: rechazar solapamientos y permitir turnos consecutivos y unidades distintas en paralelo.
- **Acción del agente:** Generó la validación de intervalos en `reservas.py` junto con sus respectivas pruebas unitarias.
- **Decisión humana:** Revisé el código generado, ejecuté la suite de pruebas y consulté la disponibilidad manualmente. Como todo funcionaba de manera impecable y respetaba los bordes, acepté la implementación sin modificaciones.
- **Evidencia:** `reservas.py`; `tests/test_reservas.py`; comandos de prueba ejecutados en mi entorno local.

### Episodio 2: cancelación con historial

- **Objetivo/requisito:** Cancelar una reserva manteniendo su identificador y datos en el sistema, liberando al mismo tiempo el horario.
- **Contexto e instrucción:** Pedí al agente añadir el soporte para cancelar reservas conservando el registro histórico y asegurando que las consultas de disponibilidad omitan las canceladas.
- **Acción del agente:** Introdujo el estado `cancelled` y ajustó los filtros de disponibilidad.
- **Decisión humana:** Probé el comando de cancelación por consola. Observé que conservaba el mismo ID, modificaba el estado a `cancelled` y que la consulta posterior devolvía `available: true`. Acepté el flujo directamente.
- **Evidencia:** `reservas.py`; prueba `test_cancellation_keeps_record_and_releases_interval` en `tests/test_reservas.py`.

### Episodio 3: persistencia y recuperación

- **Objetivo/requisito:** Asegurar que las reservas (activas y canceladas) persistan tras detener y reiniciar la aplicación.
- **Contexto e instrucción:** Solicité la implementación de almacenamiento en JSON y un mecanismo de prueba integral que simule reinicios de procesos.
- **Acción del agente:** Programó la capa de persistencia en JSON y una prueba de integración basada en procesos CLI independientes.
- **Decisión humana:** Ejecuté la suite completa y comprobé por mi cuenta que las reservas se mantenían intactas tras simular el reinicio del sistema mediante procesos separados. Acepté el comportamiento validado.
- **Evidencia:** `reservas.py`; `main.py`; prueba `test_active_and_cancelled_reservations_survive_process_restart` en `tests/test_reservas.py`.

### Verificación registrada

Se documentan tanto la ejecución inicial del agente como mi validación posterior de los resultados.

| Acción / Responsable | Comando / Procedimiento | Resultado observado |
| --- | --- | --- |
| **Agente** | `C:/Users/manu/AppData/Local/Microsoft/WindowsApps/python3.12.exe -m unittest discover -s tests -v` | Python 3.12.10; 9 pruebas, `OK`, incluida persistencia entre procesos |
| **Manuela** | `python -m unittest discover -s tests -v` | 9 pruebas pasaron con éxito (`OK`) |
| **Manuela** | `python main.py inventory`, `availability`, `reserve`, `reservations`, `cancel` y consulta de disponibilidad | Inventario correcto; reserva creada como `active`; cancelación preservó el ID y devolvió `cancelled`; disponibilidad posterior en `true` |

La suite utiliza fechas fijas de noviembre de 2026 para garantizar independencia de la fecha de ejecución. Confirmé mi conformidad y aceptación total del comportamiento probado.