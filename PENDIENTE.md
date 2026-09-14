<!-- ÚNICA lista de pendientes del proyecto. La imprime `arranque.py` al empezar
     cualquier sesión. Antes estaba repartida entre EMPEZAR_AQUI.md §7,
     SIGUIENTES_PASOS.md §3 y las entradas de PROJECT_STATUS.md, que es como se
     pierden cosas. Si algo se termina, se TACHA aquí, no en los otros tres.

     Reescrito el 10-09-2026 tras integrar los 32 commits del 28-08 que llevaban
     sin fusionar: la versión anterior de esta lista mandaba a buscar un fichero
     que nunca existió y describía un paso ya superado. Las líneas que empiezan
     por <!-- no se imprimen.

     Actualizado el 14-09-2026: el punto 1 decía "ES LO SIGUIENTE, Y LO ÚNICO" y
     mandaba a empezarlo, cuando la sesión local de ese mismo día ya lo había
     ejecutado con resultado (dos casos cuadrando exacto) y había arreglado un
     bug real por el camino. Siete commits sin una línea aquí: exactamente lo que
     la cabecera de este fichero dice que no puede pasar. -->

  TODO LO QUE QUEDA ES SESIÓN LOCAL, en el PC de la asesoría.
  Estado del motor al 28-08-2026, medido sobre el corpus real:
    ROJO 3,03%  ·  ÁMBAR 12,82%  (bajó desde 28,28% con los arreglos de ese día)

  Rutas reales:
    corpus ContaPlus (.DAT, 2016-2026)   C:\Users\SERVILAB\Desktop\100% contabilidad
    archivo de modelos AEAT presentados  \\PC01\Documentos

  ═════════════════════════════════════════════════════════════════════
  1 · EL CUADRE CONTRA EL 303 PRESENTADO   <- EN MARCHA, YA CON RESULTADO
  ═════════════════════════════════════════════════════════════════════
      Es la ÚNICA verdad externa que este proyecto va a tener nunca.
      Todo lo demás se valida contra sí mismo.

      YA MEDIDO (14-09), primeros casos reales:
          SP_C_10  ->  CUADRA EXACTO
          SP_C_11  ->  CUADRA EXACTO
          SP_C_13  ->  la diferencia coincide EXACTA, en devengado y en
                       deducible, con la cuota de ISP del propio PDF
                       (casillas 12/13, no modeladas). Nada sin explicar.

      Y un bug real encontrado por el camino, ya arreglado: el "tipo 0"
      que aparecía en las 20 fichas medidas y dejaba el TOTAL en 0,00 era
      el asiento de liquidación trimestral de IVA (o ISP). Ya no se suma
      al total, y se sigue declarando aparte.

      ─── LO SIGUIENTE, en este orden ───

      [ ] A · REGRESIÓN PRIMERO, y es obligatoria.  El 14-09 se reescribió
          el lector de casillas del PDF: leía dígitos de DENTRO de los
          importes (el "9." de "9.999,99" le parecía la etiqueta "9.").
          PERO SP_C_10 y SP_C_11 cuadraban exacto CON EL LECTOR VIEJO, así
          que el arreglo hay que probarlo contra ellos ANTES que nada:

              python verificar_303_pdf.py --manifest verificacion_303_LOCAL.txt

          Si SP_C_10 y SP_C_11 SIGUEN cuadrando -> el arreglo es bueno,
          sigue con B.
          Si dejan de cuadrar -> el arreglo ha hecho daño. Dímelo y se
          revierte: son dos commits, no hay drama.

      [ ] B · VOLVER A MEDIR EL EXTRACTOR.  Un comando, sin trabajo manual:

              python extraer_303_pdf.py "RUTA_DEL_ARCHIVO_DE_MODELOS"

          Todo el proyecto trata la lectura de PDF con pinzas por un "1,2%
          de consistencia" que se midió DOS VECES mal: con un regex de
          importes roto (arreglado el 26-08) y con el patrón de casillas
          adivinado (arreglado el 14-09, ya con el formulario delante).
          Nadie lo ha vuelto a medir desde ninguno de los dos arreglos.
          Pégame sólo la línea "tasa de consistencia". Nunca un valor.

      [ ] C · SEGUIR AÑADIENDO CLIENTES, ahora con UNA LÍNEA por cliente.
          El manifest ya no se escribe por trimestre (14-09). Dos formas:

              CLAVE|CARPETA_DEL_CLIENTE        <- usa ésta
              CLAVE|TRIMESTRE|RUTA_AL_PDF      <- sigue valiendo

          Con la primera, el script busca solo todos los trimestres de esa
          carpeta. Diez años de un cliente: una línea, no cuarenta.

          Paso a paso:
            1) python cuadre_303_ficha.py --listar
            2) Abre esa misma copia en ContaPlus y anota qué empresa es
               cada código. Es el ÚNICO trabajo manual, y se hace una vez
               por cliente.
            3) Una línea en el manifest por cada uno:
                  CARPETA::SP_C_NN|\\PC01\Documentos\CARPETA_DE_ESE_CLIENTE
            4) En seco primero (no abre ni un PDF, ni necesita pdfplumber):
                  python verificar_303_pdf.py --manifest verificacion_303_LOCAL.txt --solo-expandir
            5) Y la pasada de verdad:
                  python verificar_303_pdf.py --manifest verificacion_303_LOCAL.txt

          El fichero del manifest DEBE llevar _LOCAL en el nombre. Por
          consola solo salen recuentos, trimestres y euros: nunca una
          clave, una carpeta ni una ruta.

      Si hace falta regenerar la base (comprobar antes si ya está hecha —
      el 28-08 se regeneró y dio 509 combinaciones y 1.204 trimestres):
           python reconstruir_303.py "C:\Users\SERVILAB\Desktop\100% contabilidad" --detalle 303_LOCAL.json
           python diag_coherencia_303.py

      CONTEXTO que sigue mandando (hallazgo del 28-08): una carpeta de
      ContaPlus NO es un cliente, es una copia con hasta 70 empresas
      dentro. Por eso `clave_cliente()` usa carpeta+código.

      Y por qué el paso 2 es manual y va a seguir siéndolo: una copia de
      ContaPlus no dice de quién es (datempre.dbf tiene 0 registros,
      DATOS.ASC 0 bytes, M390A.dbf 1.268 de 1.287 a cero). Y deducirlo de
      los importes sería circular: usarías las cifras para decidir el
      cliente y el cliente para validar las cifras.

      Umbral acordado ANTES de ver ningún número (SIGUIENTES_PASOS.md §4):
        1 trimestre no cuadra   -> se investiga ese, no se ajusta nada
        >10% no cuadran         -> hay un fallo sistemático; se busca el
                                   patrón, no se parchean casos
      Con 3 casos NO hay muestra para declararlo cerrado. Decide tú
      cuántos clientes hacen falta antes de dar el paso por bueno.

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
