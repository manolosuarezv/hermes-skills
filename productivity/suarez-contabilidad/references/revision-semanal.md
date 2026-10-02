# Revisión semanal — HTML interactivo de aprobación

Manuel aprueba movimientos **una vez por semana**, no cada día. La máquina registra y el humano firma.

## Reparto de responsabilidades (no invertirlo)
- El registro automático entra con `Estado = Auto — pendiente de revisión`.
- **La máquina nunca escribe `OK`.** Solo Manuel aprueba; el `OK` sale de su clic.
- Si la propuesta automática no cuadra con la realidad, se anota el descuadre y se pregunta — nunca se "cuadra" borrando ni inventando.
- Drive se sincroniza **solo** en la revisión del domingo, y solo con lo aprobado. No tocar Drive el mismo día en que se registra.

## Cadencia
Dos jobs de cierre/backup siguen intactos (23:30 cierre, 00:00 backup). La revisión semanal es el **domingo 11:00** y es la única que entrega a todos los canales (`deliver: all`). Los `Auto` que se acumulan durante la semana viajan a RAID y a Drive el domingo, no antes.

## Generador
`scripts/revision_semanal.py` — lee el libro **en solo-lectura**, nunca escribe, y emite un HTML **autocontenido** en `revision/revision_<fecha>.html`.

- Un HTML autocontenido (CSS y datos embebidos, sin dependencias externas) para que Manuel lo abra desde el chat sin fetch ni red.
- Cada fila muestra el movimiento **y su trazabilidad** (canal de origen, soporte, estado).
- Id de movimiento con la forma `pestaña|fila|fecha` — es lo que viaja en el clic; verificar que llega **idéntico** antes de confiar en el flujo.
- Botones por fila y botones globales (aprobar/rechazar todo lo listado).

### Botones que hablan de vuelta
Conectar cada botón a `data-hermes-send="…"` para que el clic vuelva como turno. El prompt debe poder resolverse a un único movimiento; el id `pestaña|fila|fecha` cumple eso.

## Modo `--demo` (obligatorio para mostrar sin riesgo)
Cuando se genera en modo demo las filas son de MUESTRA, no movimientos reales del libro. En ese modo **deshabilitar los botones** (clase `.b-dis`, `pointer-events: none`) y rotular cada fila con una nota tipo "Fila de MUESTRA — no se registra".

Por qué: un clic sobre una fila de muestra parece una aprobación real y no lo es; sin el bloqueo, Manuel recibe un id de fila `-` y cree que aprobó algo. Nunca dejar botones vivos en demo.

## Regla de alcance
El HTML es la superficie de decisión, no el registro. Todo lo aprobado se asienta en el libro (hoja `Log de cambios` incluida) — el HTML generado es desechable y no se versiona como fuente de verdad.
