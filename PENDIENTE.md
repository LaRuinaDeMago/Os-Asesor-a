<!-- ÚNICA lista de pendientes del proyecto. La imprime `arranque.py` al empezar
     cualquier sesión. Antes estaba repartida entre EMPEZAR_AQUI.md §7,
     SIGUIENTES_PASOS.md §3 y las entradas de PROJECT_STATUS.md, que es como se
     pierden cosas. Si algo se termina, se TACHA aquí, no en los otros tres.
     Las líneas que empiezan por <!-- no se imprimen. -->

  TODO LO QUE QUEDA ES SESIÓN LOCAL, en el PC de la asesoría.
  Nada de esto necesita DPA: los tres primeros funcionan con el diseño de
  tres roles (Claude escribe el script, Diego lo ejecuta, Claude lee sólo
  recuentos). Ver .claude/rules/datos.md.

  Rutas reales:
    corpus ContaPlus (.DAT, 2016-2026)   C:\Users\SERVILAB\Desktop\100% contabilidad
    archivo de modelos AEAT presentados  \\PC01\Documentos

  ─────────────────────────────────────────────────────────────────────
  1 · REVISAR EL EMPAREJADO CLIENTE ↔ CARPETA        (minutos, sin bloqueo)
  ─────────────────────────────────────────────────────────────────────
      python emparejar_carpetas.py "C:\Users\SERVILAB\Desktop\100% contabilidad" "\\PC01\Documentos"

      Ya ejecutado el 27-08: 14 de 37 con confianza ALTA (confirmar es
      cuestión de segundos) y 23 que necesitan elegir entre 2-3 candidatos
      nombrados. Abrir `emparejado_LOCAL.txt` y decidir.
      Es el paso 1 porque desbloquea el 2.

  ─────────────────────────────────────────────────────────────────────
  2 · EL CUADRE CONTRA EL 303 PRESENTADO             (varias sesiones)
  ─────────────────────────────────────────────────────────────────────
      Es la ÚNICA verdad externa que este proyecto va a tener nunca.
      Todo lo demás se valida contra sí mismo.

      a) Regenerar la base (si no se hizo ya tras el arreglo del 27-08):
         python reconstruir_303.py "C:\Users\SERVILAB\Desktop\100% contabilidad" --detalle 303_LOCAL.json
         python diag_coherencia_303.py          (debe dar ~99% de coherencia)

      b) Vía manual, la que funciona:
         python cuadre_303_ficha.py --listar    <- SIGUIENTE COMANDO REAL
         ... elegir a mano los números que son un cliente reconocible ...
         python cuadre_303_ficha.py --elegir 2,5,9

      c) Vía automática, con el emparejado del paso 1 ya resuelto:
         python cruzar_303_importes.py "\\PC01\Documentos"

      Umbral acordado ANTES de ver ningún número (SIGUIENTES_PASOS.md §4):
        1 trimestre no cuadra   -> se investiga ese, no se ajusta nada
        >10% no cuadran         -> hay un fallo sistemático; se busca el
                                   patrón, no se parchean casos

  ─────────────────────────────────────────────────────────────────────
  3 · LAS 91 FACTURAS FOTOGRAFIADAS                  (una tarde)
  ─────────────────────────────────────────────────────────────────────
      python validar_captura_historica.py "ruta/al/fichero.csv" --columna-humano CORRECTO

      Lo ÚNICO que puede hablar de FALSOS VERDES — el retro-semáforo no
      puede, por construcción. Hay que encontrar el fichero primero.

      Umbral acordado ANTES de ver el número:
        ≥ 1 falso verde         -> SE PARA LA AUTOMATIZACIÓN. Caso por caso.
        0 sobre ≥30 juzgadas    -> no es "el motor no da falsos verdes",
                                   es "no hemos visto ninguno en 30"

      Qué esperar, para no confundir un resultado con un fallo: si el CSV
      trae base/IVA/total pero no el desglose por tipos, las del 21% y del
      0% saldrán VERDE o ROJO y las de tipos intermedios saldrán ÁMBAR
      [FALTA DATO]. Eso no es el motor fallando: es el motor negándose a
      afirmar una composición que no puede comprobar.

  ─────────────────────────────────────────────────────────────────────
  4 · LO QUE NO ES CÓDIGO, y lleva abierto desde el 12-08
  ─────────────────────────────────────────────────────────────────────
      [ ] Cifrar el USB de copia.  15 minutos. Es lo de MAYOR impacto por
          coste de toda esta lista, y lleva más de un mes abierto.
      [ ] Clave de recuperación del cifrado, guardada FUERA del equipo.
      [ ] Confirmar si la copia del USB incluye modelos, escrituras y DNI,
          o sólo contabilidad.

  ─────────────────────────────────────────────────────────────────────
  LO QUE NO SE HACE (decidido, no pendiente)
  ─────────────────────────────────────────────────────────────────────
      · Guards nuevos sin un caso real que los pida (CLAUDE.md).
      · Nada de laboral ni mercantil todavía.
      · Nada de DIRECCION_PRODUCTO.md: está al otro lado del DPA.
      · Vender datos de clientes en cualquier forma: LÍNEA ROJA, descartado
        y no aplazado (.claude/rules/datos.md).
      · Auto-fix de pull requests en este repositorio.
