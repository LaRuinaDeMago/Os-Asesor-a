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

  ┌───────────────────────────────────────────────────────────────────┐
  │ ANTES DE NADA, UNA SOLA VEZ (15-09-2026):                         │
  │                                                                   │
  │     git checkout master                                           │
  │     git pull                                                      │
  │                                                                   │
  │ Todo el trabajo del 14 y 15 está YA FUSIONADO en master. La rama  │
  │ `claude/github-retomada-o4zyic` no lleva nada que master no tenga:│
  │ si sigues en ella, trabajas en un sitio que nadie más mira.       │
  │                                                                   │
  │ Y no vuelvas a compartir una rama larga entre el PC y la nube     │
  │ (CLAUDE.md, regla del 11-09, con incidente real detrás): cada     │
  │ sesión crea la suya, la fusiona a master al terminar, y la borra. │
  │ master es el único punto de encuentro.                            │
  └───────────────────────────────────────────────────────────────────┘

  TODO LO QUE QUEDA ES SESIÓN LOCAL, en el PC de la asesoría.
  Estado del motor al 28-08-2026, medido sobre el corpus real:
    ROJO 3,03%  ·  ÁMBAR 12,82%  (bajó desde 28,28% con los arreglos de ese día)

  Rutas reales:
    corpus ContaPlus (.DAT, 2016-2026)   C:\Users\SERVILAB\Desktop\100% contabilidad
    archivo de modelos AEAT presentados  \\PC01\Documentos

  ═════════════════════════════════════════════════════════════════════
  1 · EL CUADRE CONTRA EL 303 PRESENTADO   <- A Y B CERRADOS, VER PASO C
  ═════════════════════════════════════════════════════════════════════
      Es la ÚNICA verdad externa que este proyecto va a tener nunca.
      Todo lo demás se valida contra sí mismo.

      [X] A · CONFIRMADO CON DATOS REALES (15-09-2026, sesión local):
          3 clientes, 9 trimestres —

              casos totales : 9   cuadran exacto : 2
              cuadran con redondeo (<=1 EUR) : 6
              NO cuadran : 1 (SP_C_13 -- explicado ENTERO por ISP,
                              formacion facturada por proveedor
                              extranjero sin IVA, confirmado por Diego)
              lectura correcta : 9/9

          SP_C_10 y SP_C_11 (los que ya cuadraban con el lector viejo):
          SIN REGRESION, y con mas cobertura que antes (4 trimestres cada
          uno, no solo el ya probado). El umbral de SIGUIENTES_PASOS.md §4
          sigue sin alcanzarse con solo 3 clientes -- ver punto C para
          ampliar la muestra cuando toque, no es urgente.

          Por el camino, TRES bugs reales encontrados y cerrados (detalle
          completo en PROJECT_STATUS.md, 15-09, octava entrada -- sesion
          local):
            1) extraer_casillas() se quedaba con la PRIMERA aparicion de
               una etiqueta de casilla, aunque no llevara importe detras
               (la formula impresa del propio 303 repite las etiquetas
               sueltas). Arreglado con localizar_valor_casilla(), que
               prueba todas las apariciones.
            2) verificar_303_pdf.py tenia su PROPIA suma de la
               contabilidad, y nunca recibio el arreglo del "tipo 0" que
               ya tenia cuadre_303_ficha.py desde el commit 6b2acb2 --
               mismo bug, dos sitios. Ya arreglado en los dos.
            3) explicar_por_isp() solo comprobaba la CUOTA de ISP, nunca
               la BASE, y aplicaba el ajuste aunque un lado ya cuadrara
               sin el (mensaje falso de "sin explicar"). Ahora comprueba
               los dos y solo ajusta donde hace falta -- Y donde AYUDA
               (revision de rigor antes del push, mismo dia: sumar el ISP
               a una diferencia real y sin relacion con la ISP la podia
               EMPEORAR en vez de explicarla. Sin caso real todavia --
               cerrado con un ejemplo inventado, como el resto de guardas).

          Herramienta nueva para diagnosticar sin ver un dato:
          `diag_orden_extraccion_pdf.py` -- nunca imprime contenido del
          PDF, solo distancias en caracteres y booleanos.

      CÓMO LEER EL RESUMEN, para referencia (ya no hace falta explicarlo
      cada vez, pero queda aquí por si otra sesión lo necesita). Trae DOS
      bloques, y el segundo se lee PRIMERO:

        1) ¿Se ha leído bien el PDF?   <- ESTE PRIMERO
           El impreso se cuadra contra SU PROPIA aritmética, la que lleva
           escrita al lado de cada total:
               27 = 152+167+03+155+06+09+11+13+15+158+170+18+21+24+26
               45 = 29+31+33+35+37+39+41+42+43+44
               46 = 27 - 45
           Si eso cuadra al céntimo, la lectura es buena. Tres estados:
               lectura correcta      -> fíate del bloque 2
               lectura INCORRECTA    -> el descuadre es DEL LECTOR.
                                        Mira ese PDF, no el asiento
               sin poder comprobarla -> NO es un aprobado

        2) ¿Cuadra contra la contabilidad?
           Si NO cuadra contra 03+06+09 (régimen general) pero SÍ contra
           las casillas 27/45 (los totales del propio modelo), el script
           te lo dice con estas palabras:
               "la diferencia de arriba es de CASILLA, no de contabilidad"
           Y si el 303 declara prorrata (44), bienes de inversión (43),
           REAGP (42), rectificación de deducciones (41), importaciones
           (33/35) o recargo de equivalencia, avisa aparte:
               ESTE 303 DECLARA COSAS QUE NUESTRA RECONSTRUCCION NO PUEDE TENER
           Esos casos NO PUEDEN cuadrar y no es un defecto de nadie -- la
           reconstrucción sale sólo de las cuentas 477/472 por tipo.

           La casilla 44 (prorrata) "se cumplimentará ÚNICAMENTE EN EL 4T
           O MES 12" (cita AEAT, 15-09) -- un cliente con prorrata tiene
           1T/2T/3T perfectamente comparables, sólo se escapa el 4T.

           LO QUE HAY QUE DECIDIR (es tuyo, no del script): cuál de las
           dos comparaciones manda como veredicto oficial. Ahora se
           declaran las dos y el veredicto lo sigue dando 03+06+09.
           Cambiarlo es una decisión contable, no técnica.

      [X] B · MEDIDO (15-09-2026, sesión local): **1,2% -> 99,8%**.

              python extraer_303_pdf.py "\\PC01\Documentos"

          1.023 documentos 303 reconocidos (antes se citaba 1.168 --
          diferencia anotada, no alarmante, probablemente el archivo
          cambia con el tiempo). 938 de 940 tramos cuadran. Supera con
          margen amplio el umbral que el propio script tiene escrito de
          antemano (">95% = extraccion fiable"). Confirma a escala completa
          lo que ya se habia visto en 3 clientes / 9 trimestres: los tres
          arreglos del 15-09 (casilla 07, tipo 0, base de ISP) no eran un
          parche para un caso concreto.

          Los 2 tramos que NO cuadran (0,2%) se dejan anotados, sin
          perseguir: el umbral ya estaba decidido de antemano y se cumple
          con margen de sobra -- construir una herramienta nueva para 2
          casos, sin ningun indicio de que sean sistematicos, seria
          precision de mas sin necesidad real detras (CLAUDE.md). Si algun
          dia aparecen mas casos parecidos, aqui es donde retomar.

      [ ] C · AÑADIR MÁS CLIENTES, con UNA LÍNEA por cliente.
          El manifest ya no se escribe por trimestre (14-09). Dos formas:

              CLAVE|CARPETA_DEL_CLIENTE        <- usa ésta
              CLAVE|TRIMESTRE|RUTA_AL_PDF      <- sigue valiendo

          Con la primera, el script busca solo todos los trimestres de esa
          carpeta y de sus subcarpetas. Diez años de un cliente: una línea,
          no cuarenta.

          Paso a paso:
            1) python cuadre_303_ficha.py --listar
            2) Abre esa misma copia en ContaPlus y anota qué empresa es
               cada código. Es el ÚNICO trabajo manual, y se hace una vez
               por cliente, para siempre.
            3) Una línea en el manifest por cada uno:
                  CARPETA::SP_C_NN|RUTA_A_LA_CARPETA_DE_ESE_CLIENTE
            4) En seco primero — no abre ni un PDF, ni necesita pdfplumber:
                  python verificar_303_pdf.py --manifest verificacion_303_LOCAL.txt --solo-expandir
               Te dice, por número de entrada, a cuántos trimestres expande
               cada línea y qué deja fuera (y por qué: carpeta que no
               existe, clave que no está en el JSON, dos PDF que dicen ser
               el mismo trimestre...).
            5) Y la pasada de verdad, sin --solo-expandir.

          El fichero del manifest DEBE llevar _LOCAL en el nombre. Por
          consola sólo salen recuentos, trimestres y euros: nunca una
          clave, una carpeta ni una ruta.

          ACORDADO 15-09-2026: el manifest es PERMANENTE, solo crece.
          Nunca se recrea desde cero ni se recorta a un solo cliente para
          una prueba puntual -- eso fue justo lo que pasó esta sesión con
          SP_C_10/SP_C_11 (ya resueltos el 14-09, pero el manifest solo
          tenía a SP_C_13) y costó tiempo recuperarlo. El paso 2 (abrir
          ContaPlus, anotar el código) es "una vez por cliente, para
          siempre" SOLO si el resultado no se pierde entre sesiones.

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
  2 · NORMATIVA: LO LEÍDO EN EL BOE, Y LO QUE HAY QUE DECIDIR
  ═════════════════════════════════════════════════════════════════════
      Del registro creado el 15-09 (`python fuentes_externas.py`). No
      corre prisa como el 303, pero es trabajo tuyo y de nadie más:
      un asesor con el texto delante, cinco minutos cada uno.

      YA LEÍDO EN EL BOE (15-09, texto consolidado, artículo por
      artículo). Lo que queda es DECIDIR, no buscar:

      [ ] A · `TABLA_IVA_4` — tres hallazgos, ninguno tocado porque
          cambiar la tabla mueve el motor y es decisión contable tuya:
            · El ACEITE DE OLIVA **ya no es temporal**: el RD-ley
              4/2024 lo dejó al 4% de forma permanente desde el
              1-1-2025. La alarma queda resuelta, y en el sentido bueno.
            · Pero la tabla dice **"pan"** y la ley dice **"pan COMÚN"**.
              Un pan especial va al 10% y esta tabla lo aprobaría al 4%.
              Igual con fruta/verdura/…: la ley exige que sean
              "productos naturales según el Código Alimentario".
            · Y **falta media lista**: el art. 91.Dos incluye también
              libros, periódicos y revistas, medicamentos de uso humano,
              vehículos para movilidad reducida y prótesis. Una factura
              de libros al 4% saldría marcada como tipo incorrecto.
          Decide tú si se afina la tabla o se deja como está.

      [ ] B · `TIPOS_LEGALES = (0, 4, 5, 10, 21)`. **Cuatro confirmados**
          en el BOE: 21% (art. 90.Uno), 10% (art. 91.Uno), 4%
          (art. 91.Dos) y 0% (art. 91.Cuatro, donativos — existe y es
          permanente). **El 5% NO aparece** ni en el 90 ni en el 91: era
          un tipo temporal.
          **Y probablemente haya que dejarlo igual:** esa tupla la usa
          el LECTOR DE PDF para validar su propia lectura sobre un
          archivo de 2016 a 2026, y en parte de ese periodo el 5% sí
          estuvo vigente. Sería incorrecto reutilizarla para validar una
          factura de hoy. Sólo hay que decidirlo y anotarlo.

      [ ] C · Las citas de `autoridad_guards.py`: **8 de 16 ya están
          VERIFICADAS** contra el texto consolidado (arts. 78, 84, 88,
          90, 91 y 154). Quedan 8 PROPUESTAS, que son las de fuera de la
          LIVA: Reglamento de facturación (RD 1619/2012), retenciones de
          IRPF (RD 439/2007) y la composición del NIF. Se leen igual —
          dímelo y las traigo.

      [ ] D · **Vigilancia automática, ya montada.** Un comando:
                  python boe_normativa.py --comprobar
          Descarga del BOE los artículos registrados y avisa si alguno
          ha cambiado desde que se leyó. No interpreta el cambio: lo
          detecta y te manda a leerlo. Merece la pena dejarlo en una
          tarea programada mensual.

  ═════════════════════════════════════════════════════════════════════
  3 · LO QUE NO ES CÓDIGO, y lleva abierto desde el 12-08
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
