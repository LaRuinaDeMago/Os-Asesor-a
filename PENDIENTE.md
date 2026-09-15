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
  │ RAMAS — comprobado y cerrado el 15-09-2026                        │
  │                                                                   │
  │ Ya no hay nada que hacer aquí. Medido, no recordado: la única     │
  │ rama local es `master`, y `master` y `origin/master` están al     │
  │ día la una con la otra (0 commits de diferencia en los dos        │
  │ sentidos). La antigua `claude/github-retomada-o4zyic` lleva CERO  │
  │ commits que master no tenga — está estrictamente atrasada.        │
  │                                                                   │
  │ Lo que SÍ sigue vigente, y es permanente (CLAUDE.md, regla del    │
  │ 11-09, con incidente real detrás): nunca compartir una rama larga │
  │ entre el PC y la nube. Cada sesión crea la suya, la fusiona a     │
  │ master al terminar, y la borra. master es el único punto de       │
  │ encuentro.                                                        │
  │                                                                   │
  │ (Antes aquí había un "ANTES DE NADA, UNA SOLA VEZ: git checkout   │
  │ master && git pull". Estaba hecho desde el mismo día que se       │
  │ escribió, y era lo PRIMERO que leía cada sesión al arrancar:      │
  │ una instrucción ya cumplida ocupando el sitio de la que importa.) │
  └───────────────────────────────────────────────────────────────────┘

  ═════════════════════════════════════════════════════════════════════
  EL ORDEN — por dónde seguir, y por qué en ese orden
  ═════════════════════════════════════════════════════════════════════
      Escrito el 15-09-2026 al cerrar la sesión. Existía como conclusión
      razonada pero **no estaba en ningún fichero**, que es exactamente
      como se pierden las cosas en este proyecto (tres veces en un mismo
      día: los lotes, el albarán y los certificados vivían sólo en prosa).

      El motor VALIDA, pero todavía no HACE nada: no lee una factura, no
      la mete en ContaPlus, no te ahorra un minuto. Todo el valor está
      detrás de dos puertas que aún no se han cruzado. Por eso el orden
      no es "lo que sea más cómodo", es éste:

      1 · LA DECISIÓN DEL DPA. Es la puerta única. Sin ella el modelo no
          puede VER una factura, y toda la cadena OCR→motor→ContaPlus
          espera detrás. No es técnica: es contratar API/Consola de
          Anthropic (ver `.claude/rules/datos.md`). **Nada de lo demás la
          sustituye, y cuanto más motor se construya antes de cruzarla,
          más se construye a ciegas.**

      2 · UNA FACTURA REAL DE PUNTA A PUNTA. Foto → motor → asiento en
          ContaPlus. **Una**, no un lote. Es "Puerta 1 antes que Puerta
          2" de `ARQUITECTURA_DATOS.md` §4 — la regla que este proyecto
          ya ha violado cuatro veces, y las cuatro costaron caro.

      3 · DOS O TRES LOTES CRONOMETRADOS (punto 4.A). Gratis, sin trabajo
          extra, y son los que deciden la economía real del proyecto: hoy
          todo descansa en UNA medición de 30 facturas.

      4 · TODO LO DEMÁS. Más clientes en el cuadre 303 (1.C), el modelo
          130 (1.D), las citas que faltan (2.C-bis). Valioso, pero
          secundario mientras 1 y 2 sigan abiertos.

      ─────────────────────────────────────────────────────────────────
      Y UN CRITERIO PARA SABER CUÁNDO DEJAR DE PULIR
      ─────────────────────────────────────────────────────────────────
      El rigor de este proyecto se paga solo **mientras cada repaso
      encuentre algo**. El 15-09 encontró dos defectos reales en el motor
      (el validador de NIF de la triangulación y un `return "OK"`
      atrapalotodo) y un impreso del 303 cambiado en enero de 2026 que
      nadie sabía.

      > **El día que un repaso completo no encuentre nada, ésa es la
      > señal de que toca dejar de reforzar y empezar a entregar.**
      > No antes — pero tampoco mucho después.

      La razón por la que se aprieta tanto sigue siendo la correcta, y es
      de Diego: *un motor que falla y hay que estar comprobando siempre es
      peor que hacerlo a mano*. Pero eso justifica **validar** con este
      rigor, no **construir a lo ancho** sin validar. No son lo mismo, y
      confundirlas es el error que ya está documentado cuatro veces.

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

      [X] D · ESTRUCTURA DE PC1 MEDIDA (15-09-2026). Confirmado: organizada
          por cliente (88,6% de las 140 carpetas de primer nivel son
          planas o de 1 nivel, tamaño moderado). Pero solo el 24,0% de los
          14.395 PDF se identifica por modelo+numero en el nombre --
          confirmado por dos metodos independientes (3.459 vs 3.422).
          Desglose por modelo, solo PDF: 303=1.154, 130=535, 111=482,
          390=256, 347=199, 202=187, 115=184, 036=178, 349=127, 190=116,
          180=48. Detalle completo en PROJECT_STATUS.md (15-09, decima
          entrada). Herramienta: `explorar_estructura_pc1.py`.

          Dos preguntas abiertas de la misma pasada, sin resolver:
            - 2.198 ficheros `.dat` dentro de PC1 -- ¿son contenedores de
              ContaPlus tambien, como los de "100% contabilidad"?
            - 2.360 ficheros `.tgd` -- formato sin identificar, segunda
              extension mas comun tras PDF y JPG. ¿Que programa lo genera?

          Si se retoma "extrapolar el 303 a otros modelos": el candidato
          con mas volumen (aparte del 303, ya resuelto) es el 130, no el
          390 -- el 390 seguia siendo el "casi gratis" por poder
          contrastarse contra los 4 trimestres de 303 ya extraidos, pero
          en volumen puro el 130 dobla al 390.

      [ ] F · ⚠️ EL IMPRESO DEL 303 CAMBIÓ EL 27-01-2026 Y HAY QUE
          MIRARLO. Detectado el 15-09-2026 al montar `modelos_aeat.py`:
          el ANEXO I de la Orden EHA/3786/2008 está en vigor desde el
          **27-01-2026** (Orden HAC/27/2026). El anexo es donde vive la
          FORMA del impreso, que es justo sobre lo que está construido
          `extraer_303_pdf.py`.

          **Por qué no es una emergencia:** los 1.023 documentos ya
          leídos y validados (99,8%) son históricos y siguen valiendo.

          **Por qué no se puede dejar pasar:** afecta a lo que se lea de
          2026 en adelante, y un impreso que cambia **no rompe el lector
          con un error, lo rompe dando números**.

          **Qué hay que hacer, y es trabajo de asesor, no de programa:**
          coger un 303 presentado de 2026 y comprobar si las casillas que
          usa el lector siguen donde estaban. El programa detecta el
          cambio; interpretarlo no lo hace ni lo hará.

          (Detalle que explica por qué no se había visto: el **art. 1** de
          esa misma Orden tiene redacción de 2017. Vigilar el articulado
          no habría detectado nada — el cambio estaba en el anexo.)

      [ ] E · UN UMBRAL QUE DESCARTA DATOS Y NADIE HA MEDIDO (15-09-2026).
          `enlazador_clientes_303.py` y `diag_verificar_carpeta_cliente.py`
          llevan `MIN_NIFS = 3`, y en el primero **filtra de verdad**
          (lineas 160 y 181: los cubos con menos de 3 contrapartes se caen
          antes de enlazar). Comprobado: **ningun documento justifica ese
          3**. Lo unico escrito sobre este umbral es que el `5` original
          de `fase0_huella_cliente.py` fue *"una eleccion arbitraria sin
          medir"* (`FASE0_RESULTADOS.md` §369) que descarto 106
          contenedores -- entre ellos un bulto de 40 con exactamente 3 NIF
          con pinta de autonomos pequenos. Por eso `fase0_reagrupa.py` lo
          bajo a 1.

          **NO se ha cambiado a proposito.** Bajarlo a ojo seria repetir
          exactamente el mismo error en sentido contrario. Lo que toca es
          medirlo: cuantos cubos caen con 3, con 2 y con 1, y si los que
          caen son clientes reales pequenos o ruido. Hasta entonces queda
          declarado como **no comprobado, que no es un aprobado**.

  ═════════════════════════════════════════════════════════════════════
  2 · NORMATIVA: LO LEÍDO EN EL BOE, Y LO QUE HAY QUE DECIDIR
  ═════════════════════════════════════════════════════════════════════
      Del registro creado el 15-09 (`python fuentes_externas.py`). No
      corre prisa como el 303, pero es trabajo tuyo y de nadie más:
      un asesor con el texto delante, cinco minutos cada uno.

      YA LEÍDO EN EL BOE (15-09, texto consolidado, artículo por
      artículo). Lo que queda es DECIDIR, no buscar:

      [X] A · `TABLA_IVA_4` — RESUELTO 15-09-2026 (sesión local). Añadidos
          los 4 apartados que faltaban del art. 91.Dos LIVA (2º-5º): libros/
          periódicos/revistas, medicamentos de uso humano, vehículos para
          movilidad reducida, prótesis. El aceite de oliva ya estaba bien
          (permanente desde 2025, RD-ley 4/2024).
          **"pan"/fruta/verdura se dejan SIN TOCAR, a propósito** — riesgo
          declarado, no resuelto: la ley exige "pan COMÚN" y "productos
          naturales según el Código Alimentario", y un string suelto no
          distingue eso de un pan especial o un procesado. Arreglarlo de
          verdad exige que la captura declare esa distinción, que no existe
          todavía. **Y no afecta a ninguna factura real hoy de todas formas:**
          `guard_tipo_producto_iva_semantico` está DORMIDO en producción —
          confirmado por grep, nada en el pipeline real produce
          `categoria_producto` todavía. Test antes/después (regla de
          contabilidad.md): 65/65 los dos. Commit `0360d43`.

      [X] B · `TIPOS_LEGALES = (0, 4, 5, 10, 21)` — RESUELTO 15-09-2026.
          Decidido mantener el 5% aunque ya no exista en el BOE vigente:
          esta tupla valida la lectura de un archivo de 2016-2026, y en
          parte de ese periodo el 5% sí estuvo legal. Documentado en el
          propio código (comentario junto a la constante). Commit `0360d43`.

      [ ] C · Las citas de `autoridad_guards.py`: **8 de 16 ya están
          VERIFICADAS** contra el texto consolidado (arts. 78, 84, 88,
          90, 91 y 154). Quedan 8 PROPUESTAS, que son las de fuera de la
          LIVA: Reglamento de facturación (RD 1619/2012), retenciones de
          IRPF (RD 439/2007) y la composición del NIF.

          ✅ **RESUELTO 15-09-2026. De 8 verificadas a 15 de 16**, y la que
          falta está declarada PARCIAL a propósito, no olvidada.

          Leídos en el texto consolidado, artículo por artículo:
            LIVA         a13 (hecho imponible), a15 (concepto de AIB),
                         a20 (exenciones interiores), a75 (devengo),
                         a99 (ejercicio del derecho a la deducción)
            RD 1619/2012 a6 (contenido de la factura), a15 (rectificativas)
            RD 439/2007  a74 (obligación de retener)
            Orden EHA/451/2008  a2 a a5 (composición del NIF)

          **El hallazgo que importa, y es un límite real:**
          `guard_nif_digito_control` CALCULA el carácter de control, y ese
          **algoritmo no está en el texto legal de ninguna de las dos
          normas** que regulan el NIF — la Orden se acaba en el art. 5 y
          el RD 1065/2007 art. 22 sólo delega ("en los términos que
          establezca el Ministro"). Es especificación técnica de la AEAT,
          no artículo citable. Por eso PARCIAL: la composición sí está
          verificada, el algoritmo no. Llamarlo VERIFICADO sería el mismo
          falso verde de siempre.

          Dos correcciones de camino, por comprobar en vez de suponer:
            - Esta línea decía que las 8 restantes eran "las de fuera de
              la LIVA". **Falso:** cinco artículos eran de la LIVA.
            - La Orden del NIF se citaba con un identificador BOE que da
              404 contra la API. El real es `BOE-A-2008-3580`.

          Y el arreglo de fondo, que vale más que las citas:
          `--comprobar` sólo vigilaba `fuentes_externas` (**2 artículos**).
          Las citas verificadas de `autoridad_guards` se guardaban con su
          bloque pero **sin huella**, así que no las vigilaba nadie. Ahora
          las huellas viven en una tabla única (`HUELLAS`) y la
          comprobación cubre **18 artículos**. Ejecutado de verdad:
          *18 sin cambios, 0 cambiados, 0 no comprobados.*

      [X] C-ter · LOS IMPRESOS DE LOS MODELOS, VIGILADOS — 15-09-2026.
          Pregunta de Diego: ¿esto del BOE se puede hacer con todos los
          modelos del año laboral (303, 130, 111, 115, 347, 349)?
          **Sí, y resultó más urgente de lo que parecía.**

          El lector del 303 está construido sobre la FORMA del impreso
          (dónde cae cada casilla, qué aritmética imprime). Esa forma la
          fija el ANEXO de una Orden ministerial. Si el anexo cambia, el
          impreso cambia — y el extractor **no da error: da números**.
          Es el peor fallo posible aquí, y ningún test puede verlo,
          porque los tests usan el impreso viejo.

          **Medido al montarlo, y nadie lo sabía:**
              modelo 303  ANEXO I -> en vigor desde 20260127 (HAC/27/2026)
              modelo 347  ANEXO   -> en vigor desde 20251213 (HAC/1431/2025)

          Los dos cambiaron en los últimos nueve meses. **Queda por
          mirar si el cambio del 303 afecta a las casillas que usa
          `extraer_303_pdf.py`** — eso lo lee un asesor, no un programa.

          Montado `modelos_aeat.py` (5 bloques de 4 Órdenes: 303, 130,
          347 ×2, 349), enganchado a `boe_normativa.py --comprobar`, que
          pasa a vigilar **23 bloques**. Ejecutado de verdad: *23 sin
          cambios, 0 cambiados, 0 no comprobados.*

          OJO al ampliarlo: el nombre del bloque del anexo **no es
          uniforme** entre Órdenes (el 303 usa `ani`, el 130 usa `ai`).
          Se mira con `modelos_aeat.indice("BOE-A-...")`.

      [~] C-quater · MODELOS QUE FALTAN POR IDENTIFICAR — AVANZADO
          15-09-2026 (sesión Cloud), no cerrado del todo. Ninguna Orden se
          registró a ojo: cada `BOE-A-` se confirmó contra la propia API
          del BOE (`modelos_aeat.indice(...)`), el mismo motivo por el que
          esto llevaba abierto — un primer intento a ojo con la Orden del
          NIF devolvió una resolución sobre equipos termosifón. Adivinar
          un `BOE-A-` no sale barato.

          **Dos ya registrados y vigilados de verdad, en `MODELOS`:**
            - `390` — Orden EHA/3111/2009 (BOE-A-2009-18472), ANEXO I.
              Cambió el 27-01-2026, MISMA fecha que el 303 — las dos
              vienen de la Orden HAC/27/2026, que tocó los dos impresos
              a la vez y nadie lo había cruzado hasta ahora.
            - `036` — Orden EHA/1274/2007 (BOE-A-2007-9508), ANEXO I. De
              paso, un hallazgo que no estaba en la lista: el `037`
              (declaración simplificada, mismo Orden, ANEXO II) está
              **suprimido desde el 03-02-2025** — ya no se presenta, así
              que no hace falta vigilarlo aparte. `037` sale de la lista
              de pendientes, no por descuido sino porque ya no existe.

          **Tres siguen en `PENDIENTES_DE_IDENTIFICAR`, y ya NO por falta
          del `BOE-A` — el `BOE-A` de los tres está encontrado y
          verificado — sino porque forzarlos sería el mismo error que
          adivinar uno:**
            - `111` — Orden EHA/586/2011 (BOE-A-2011-4948) confirmada,
              pero su índice consolidado no trae NINGÚN bloque ANEXO.
              Nada que vigilar por huella con este mecanismo tal cual
              está — falta decidir si se vigila otra cosa (un artículo)
              o se declara no vigilable.
            - `190` — Orden EHA/3127/2009 (BOE-A-2009-18567) confirmada,
              pero su ANEXO I —el impreso— está `(Suprimido)` desde el
              13-12-2025: ya no hay formulario que fotografiar, solo
              diseños de fichero para la presentación telemática.
            - `115/180` — Orden de 20 de noviembre de 2000
              (BOE-A-2000-21430) confirmada, pero trae 6 anexos de la
              doble tarifa peseta/euro y no está claro sin un asesor cuál
              sigue vigente para cada modelo.

          **Y un hallazgo técnico de paso, que no es de este cambio sino
          que ya vivía en el `130` registrado desde el 15-09:** el ANEXO I
          del `130` y el ANEXO I de `115/180` devuelven la MISMA huella
          (`5a9ae17c78b3f6fd`) siendo documentos distintos — los dos se
          reducen al mismo texto trivial `"ANEXO I"` porque el impreso de
          verdad es una imagen sin texto extraíble. **La huella no puede
          distinguir un cambio de imagen en estos casos**; solo la fecha
          de vigencia avisaría. No es un bug de este cambio — es un límite
          del mecanismo que conviene tener presente antes de fiarse ciegamente
          de un "sin cambios" en un modelo cuyo anexo es solo imagen.

          `boe_normativa.py --comprobar` vigila ahora **25 bloques**, no
          23 — ejecutado de verdad: *25 sin cambios, 0 cambiados, 0 no
          comprobados.*

      [ ] C-bis · LO QUE QUEDÓ DECLARADO Y SIN CERRAR, para no darlo por
          hecho:
            - Los **porcentajes de retención** que reconoce
              `guard_retencion_vs_error` NO se han contrastado. El
              artículo que los ampara sí; los números no. Y son lo que
              más cambia de todo el fichero.
            - El **RD 1514/2007 (PGC)** para el supuesto de inmovilizado
              de `guard_tipo_operacion_especial` sigue sin leerse: no
              tiene la misma estructura de articulado fiscal y merece su
              propia pasada.
            - `nif_check.py` exige control-letra para `"PQSW"` y
              `triangulacion_identidad_v0.py` para `"PQRSNW"`: faltan
              **R** (congregaciones religiosas) y **N** (entidades
              extranjeras). **No se ha tocado a propósito** — la norma
              leída no fija ese algoritmo, así que cambiarlo sería
              elegirlo a ojo, el error que este proyecto ya tiene
              documentado cuatro veces. Se cierra contrastando contra la
              especificación técnica de la AEAT, no contra el BOE.

      [ ] D · **Vigilancia automática, ya montada, PENDIENTE DE DECIDIR
          EL MECANISMO (15-09-2026).** El comando en sí funciona:
                  python boe_normativa.py --comprobar
          Descarga del BOE los artículos registrados y avisa si alguno ha
          cambiado desde que se leyó. No interpreta el cambio, solo lo
          detecta.
          **Lo que quedó a medias:** se iba a montar como agente
          programado en la nube (`/schedule`), y se paró a tiempo, antes
          de crear nada, al ver que no encaja — ese mecanismo clona el
          repositorio entero y lanza una sesión de Claude Code completa
          en la nube cada mes, para un comando que no necesita ninguna
          inteligencia (el script ya compara de forma determinista) y sin
          ningún conector (Slack/email) para avisarte de verdad; te
          tocaría acordarte de mirar `claude.ai/code/routines`.
          **Lo que sí encaja:** una tarea programada de **Windows, local,
          en tu propio PC** — sin nube, sin agente de IA, Windows la
          ejecuta sola. Queda por montar la próxima vez que se retome
          este punto.

          **Y ahora vigila mucho más que cuando se escribió esto
          (15-09-2026):** pasó de 2 artículos a **18**, porque las citas
          verificadas de `autoridad_guards.py` no las miraba nadie (ver
          punto 2.C). Eso cambia lo que está en juego: ya no es "avisa si
          cambia el art. 91", es **la única forma de que las 15 citas que
          respaldan los guards no caduquen en silencio.** Sigue siendo
          una tarea de Windows de cinco minutos.

  ═════════════════════════════════════════════════════════════════════
  3 · LO QUE NO ES CÓDIGO
  ═════════════════════════════════════════════════════════════════════
      [X] Cifrar el USB de copia. RESUELTO 15-09-2026 (llevaba abierto
          desde el 12-08, más de un mes -- era lo de mayor impacto por
          coste de toda la lista).
      [ ] Clave de recuperación del cifrado, guardada FUERA del equipo.
          Es lo que queda de mayor impacto por coste de toda la lista,
          ahora que el USB está hecho: un USB cifrado cuya única clave
          vive en el equipo cifrado no protege de que se rompa el equipo.
      [ ] Confirmar si la copia del USB incluye modelos, escrituras y DNI,
          o sólo contabilidad.
      [ ] **207 certificados digitales dentro de PC1** (.pfx/.p12/.cer/
          .crt/.key/.pem), detectados por `explorar_estructura_pc1.py` el
          15-09. No son documentos: son **credenciales de acceso a la Sede
          Electrónica** de clientes. Dos cosas, las dos sin hacer:
            - Que su exclusión de cualquier procesado masivo futuro sea
              **explícita y declarada**, nunca "no coincide la extensión
              que buscábamos". Es la misma regla de siempre: lo que no se
              ha comprobado no es un OK. Un filtro por extensión que los
              deja fuera *de casualidad* no es una barrera.
            - Decidir si deben seguir donde están. Es una pregunta de
              custodia, no técnica, y es tuya.

  ═════════════════════════════════════════════════════════════════════
  4 · EL TECHO DEL MOTOR — lo que salió del flujo de trabajo real
  ═════════════════════════════════════════════════════════════════════
      Abierto el 15-09-2026. Dos revisiones externas coincidieron en la
      misma pregunta, y no había ni un dato en el repositorio para
      contestarla: **¿qué fracción del tiempo real de Diego cae dentro de
      lo que el motor sí puede hacer?** Un motor perfecto sobre el 8% del
      tiempo tiene un techo del 8%. Todo el detalle en
      `FLUJO_TRABAJO_REAL.md`; aquí sólo lo que queda por hacer.

      [ ] A · CRONOMETRAR 2-3 LOTES MÁS. Hoy existe **un solo lote**
          medido (30 facturas: ~3 min ordenar + ~4 min fotografiar +
          ~18,5 min contabilizar ≈ 51 s/factura). Un parte de horas de
          una semana se descartó explícitamente: varía demasiado entre
          semanas, meses y trimestres para ser representativo.
          Lo sostenible es mirar el reloj en lotes que ya se iban a
          organizar igual, eligiéndolos distintos entre sí: un autónomo
          con pocos proveedores, una S.L. con más volumen, y uno con
          facturas de IVA mixto.
          **No es una tarea con fecha** — se hace la próxima vez que
          toque un lote, sin agendar nada aparte.

      [ ] B · EL "ALBARÁN VALORADO" — pregunta para Diego, y **bloquea
          construir nada**. La regla "si dice ALBARÁN y no dice FACTURA,
          es un albarán" se probó con seis casos inventados y distingue
          bien lo normal. El caso que no cierra es el albarán que SÍ
          lleva precios y a veces hace de factura informal: diría
          "albarán" en el título y podría tener que tratarse como
          factura real.
          **¿Pasa eso con tus clientes, y con qué frecuencia?** Hasta
          que eso se conteste no se añade el guard — regla de CLAUDE.md:
          ningún guard sin un caso real que lo pida, y este lo tiene a
          medias.

      [ ] C · EL PGC, PERO COMO TABLA QUE UN GUARD CONSULTA — NO como
          fuente que vigilar. Decidido así el 15-09-2026, contestando a
          la pregunta de Diego de si conviene meter el Plan General
          Contable "como reforzamiento del motor".

          Comprobado que el articulado del RD 1514/2007 se lee bien
          (`BOE-A-2007-19884`). **Pero registrarlo como texto a vigilar
          no rendiría:** el PGC casi no cambia, y su articulado no es lo
          que hace falta. Lo valioso es el **cuadro de cuentas** (Parte
          quinta, en anexos), y eso no es una fuente: es una tabla.

          **El caso real que lo pide, y lo dijo Diego describiendo su
          propio flujo:** *"con proveedores conocidos es casi intuitivo
          por la experiencia; con uno nuevo o un gasto atípico, no"* —
          unos 2 minutos cada vez que aparece uno nuevo.

          `guard_cuenta_gasto_coherente` ya aprende de TU histórico qué
          cuenta usas con cada proveedor, y para los habituales eso es
          **mejor** que el PGC porque captura tu criterio real. Lo que no
          puede es proponer nada cuando el proveedor es NUEVO — que es
          justo donde se pierde el tiempo.

          **El orden correcto:** primero convertir ese guard de "te avisa
          si te desvías" a "te propone la cuenta cuando no hay
          histórico"; el cuadro de cuentas entra entonces, con un
          consumidor real. Registrarlo antes sería una fuente más en el
          inventario que ningún guard mira.

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
