<!-- ÚNICA lista de pendientes del proyecto. La imprime `arranque.py` al empezar
     cualquier sesión. Antes estaba repartida entre EMPEZAR_AQUI.md §7,
     SIGUIENTES_PASOS.md §3 y las entradas de PROJECT_STATUS.md, que es como se
     pierden cosas. Si algo se termina, se TACHA aquí, no en los otros tres.

     Reescrito el 10-09-2026 tras integrar los 32 commits del 28-08 que llevaban
     sin fusionar: la versión anterior de esta lista mandaba a buscar un fichero
     que nunca existió y describía un paso ya superado. Las líneas que empiezan
     por <!-- no se imprimen. -->

  TODO LO QUE QUEDA ES SESIÓN LOCAL, en el PC de la asesoría.
  Estado del motor al 28-08-2026, medido sobre el corpus real:
    ROJO 3,03%  ·  ÁMBAR 12,82%  (bajó desde 28,28% con los arreglos de ese día)

  Rutas reales:
    corpus ContaPlus (.DAT, 2016-2026)   C:\Users\SERVILAB\Desktop\100% contabilidad
    archivo de modelos AEAT presentados  \\PC01\Documentos

  ═════════════════════════════════════════════════════════════════════
  1 · EL CUADRE CONTRA EL 303 PRESENTADO      <- ES LO SIGUIENTE, Y LO ÚNICO
  ═════════════════════════════════════════════════════════════════════
      Es la ÚNICA verdad externa que este proyecto va a tener nunca.
      Todo lo demás se valida contra sí mismo.

      LEE ESTO PRIMERO, porque cambia el método (hallazgo del 28-08):
      una carpeta de ContaPlus NO es un cliente. Es una copia de seguridad
      con hasta 70 empresas dentro. Por eso NO sirve emparejar carpeta↔cliente,
      y por eso `clave_cliente()` usa ahora carpeta+código, no la carpeta sola.

      El camino que SÍ funciona, y no depende de resolver la identidad
      entre copias:

        a) Elegir UNA SOLA carpeta — una copia de una fecha concreta, con
           todas las empresas de ese momento dentro (p.ej. la más reciente
           de 2026).

        b) Dentro de `303_LOCAL.json`, localizar las entradas de esa carpeta.
           Cada CÓDIGO distinto dentro de ella sí identifica una empresa real
           distinta (verificado, FASE0_RESULTADOS.md §12).

        c) Diego reconoce a qué empresa corresponde cada código abriendo esa
           misma copia en ContaPlus — sin que ningún dato salga de su máquina.

        d) Con una empresa identificada, comparar sus casillas 01-09 y 28-29
           contra el 303 que esa empresa presentó ese mismo trimestre.

      Herramienta para el paso b/d, ya probada (17º auditor, 09-09):
           python cuadre_303_ficha.py --listar
           python cuadre_303_ficha.py --elegir 2,5,9

      Si hace falta regenerar la base (comprobar antes si ya está hecha —
      el 28-08 se regeneró y dio 509 combinaciones y 1.204 trimestres):
           python reconstruir_303.py "C:\Users\SERVILAB\Desktop\100% contabilidad" --detalle 303_LOCAL.json
           python diag_coherencia_303.py

      Umbral acordado ANTES de ver ningún número (SIGUIENTES_PASOS.md §4):
        1 trimestre no cuadra   -> se investiga ese, no se ajusta nada
        >10% no cuadran         -> hay un fallo sistemático; se busca el
                                   patrón, no se parchean casos

  ═════════════════════════════════════════════════════════════════════
  2 · LO QUE NO ES CÓDIGO, y lleva abierto desde el 12-08
  ═════════════════════════════════════════════════════════════════════
      [ ] Cifrar el USB de copia.  15 minutos. Es lo de MAYOR impacto por
          coste de toda esta lista, y lleva casi un mes abierto.
      [ ] Clave de recuperación del cifrado, guardada FUERA del equipo.
      [ ] Confirmar si la copia del USB incluye modelos, escrituras y DNI,
          o sólo contabilidad.

  ═════════════════════════════════════════════════════════════════════
  APARCADO — no es un pendiente, no lo busques
  ═════════════════════════════════════════════════════════════════════
      · LAS 91-93 FACTURAS FOTOGRAFIADAS.  Confirmado el 28-08: **el CSV no
        existe y nunca se creó.** Lo que hay son las 93 fotos sin procesar.
        Convertirlas en algo que `validar_captura_historica.py` pueda usar
        exige pasarlas por la captura por IA — el modelo tiene que VER la
        factura, que es justo lo que está detrás de la puerta del DPA.
        Bloqueado por dato y por DPA, no por buscar. Sin fecha.
        (La herramienta está lista y probada — 16º auditor, 09-09 — para
        cuando esa decisión se tome.)

      · La identidad de cliente ENTRE COPIAS distintas. Se probaron cinco
        vías (tres estadísticas el 27-08, más nombre y consolidación) y
        ninguna basta. El camino del punto 1 la esquiva por completo:
        no hace falta resolverla para cuadrar un 303.

  ═════════════════════════════════════════════════════════════════════
  LO QUE NO SE HACE (decidido, no pendiente)
  ═════════════════════════════════════════════════════════════════════
      · Guards nuevos sin un caso real que los pida (CLAUDE.md).
      · Nada de laboral ni mercantil todavía.
      · Nada de DIRECCION_PRODUCTO.md: está al otro lado del DPA.
      · Adjuntar un fichero real a una sesión Cloud, ni con "no lo leas"
        (incidente real del 27-08, .claude/rules/datos.md).
      · Vender datos de clientes en cualquier forma: LÍNEA ROJA, descartado
        y no aplazado (.claude/rules/datos.md).
      · Auto-fix de pull requests en este repositorio.
