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
  │ RAMAS — el estado ya NO se escribe aquí, se MIDE                  │
  │                                                                   │
  │ Aquí había un párrafo que empezaba por «Medido, no recordado» y   │
  │ daba por vaciada una rama concreta. Era cierto el día que se      │
  │ escribió —16-09-2026— y dejó de serlo ESE MISMO DÍA, en cuanto    │
  │ master avanzó tres commits. Un texto que se presenta como         │
  │ medición y en realidad se recita es la forma más cara de          │
  │ equivocarse: se lee al empezar cada sesión y se cree. Es el mismo │
  │ fallo que ya le pasó al párrafo de CLAUDE.md que citaba el tamaño │
  │ de PROJECT_STATUS.md («140 KB» cuando ya iba por 257 KB).         │
  │                                                                   │
  │ Desde el 16-09-2026 lo dice `arranque.py`, midiéndolo en el       │
  │ momento: qué ramas hay en el remoto, cuáles no tienen nada que    │
  │ master no tenga (y el comando exacto para borrarlas), y cuáles    │
  │ llevan trabajo que master no ha visto.                            │
  │                                                                   │
  │ Lo que SÍ es permanente, y va escrito porque es una REGLA y no un │
  │ estado (CLAUDE.md, 11-09-2026, con incidente real detrás): nunca  │
  │ compartir una rama larga entre el PC y la nube. Cada sesión crea  │
  │ la suya, la fusiona a master al terminar, y la borra. master es   │
  │ el único punto de encuentro.                                     │
  │                                                                   │
  │ ⚠️ EL BORRADO LO TIENES QUE DAR TÚ. Desde una sesión Cloud el     │
  │ remoto responde **HTTP 403** al refspec de borrado, aunque acepte │
  │ los push de commits. Es una denegación de autorización, no un     │
  │ fallo de red: no se reintenta, se reporta (comprobado 16-09-2026  │
  │ con las dos sintaxis, y con `recentRelayFailures` del proxy       │
  │ vacío, o sea que no es el proxy quien corta). Es de un clic en    │
  │ GitHub, o desde tu PC con el comando que imprime `arranque.py`.   │
  └───────────────────────────────────────────────────────────────────┘

  ╔═══════════════════════════════════════════════════════════════════╗
  ║ MAÑANA, SESIÓN LOCAL — EMPIEZA POR AQUÍ                           ║
  ║ Escrito el 16-09-2026 al cerrar la sesión Cloud.                  ║
  ╚═══════════════════════════════════════════════════════════════════╝

      En el PC de la asesoría el intérprete es `python`, no `python3`,
      y las variables se ponen con `set VAR=1`, no con `export`.

      ── PREPARACIÓN (una vez, ~5 minutos) ──────────────────────────

        1) git checkout master && git pull
        2) pip install -r requirements.txt
           Instala dbfread, pdfplumber, google-genai y anthropic.
        3) sh scripts/install_hooks.sh      (los hooks NO se clonan)
        4) python audit_project.py

        QUÉ ESPERAR EN EL PASO 4, y esto es nuevo: con las cuatro
        dependencias instaladas, el aviso ⚠️ de dependencias desaparece
        y la auditoría puede devolver **código 0 por primera vez**.
        46 comprobaciones en verde. Si devuelve 1, eso manda sobre todo
        lo demás y se mira antes de seguir.

        5) python modo_trabajo.py
           Te dice, medido, qué puedes hacer y qué falta encender. Si
           algo de lo de abajo no sale en verde ahí, empieza por eso.

      ── PASO 1 · EL ENSAYO EN VACÍO (haz esto ANTES que nada) ──────

      ✅ **HECHO Y CERRADO — 16-09-2026, sesión LOCAL.** Ejecutado de
      verdad, no en seco: clave de Gemini con facturación activa (nivel
      "Paid" confirmado en AI Studio, no la capa gratis), factura
      fabricada con `crear_factura_sintetica.py`, guardada como PDF
      ("FRA SINTETICA 1.pdf") y pasada por `captura_orquestador.py
      --procedencia SINTETICO` contra la API real.

      **Las cuatro preguntas de (d), contestadas:**
        · `tramos_iva` llegó con los DOS tramos, 21% y 5% — **confirmado
          contra la API real**, no solo contra el ensayo sintético. El
          arreglo del 16-09 (campos anidados) sobrevive de punta a punta.
        · El número salió `A26/7.612`, con barra y punto — correcto.
        · `total_factura_2` y `nif_margen` **NO se pudieron comprobar**:
          en esta factura fabricada el pie lleva el mismo valor que el
          cuadro, así que copiar y leer dos veces son indistinguibles.
          ✅ **YA HAY CON QUÉ CONTESTARLO (16-09-2026, sesión Cloud).**
          `crear_muestras_sinteticas.py` fabrica los documentos que
          faltaban, como IMAGEN y con la verdad conocida al lado:

              python crear_muestras_sinteticas.py

          Escribe `muestras_sinteticas/` (no se versiona) con tres
          recetas, cada una en versión limpia Y degradada, y un
          `_verdad.json` por receta con los NOMBRES DE CAMPO DEL
          CONTRATO — así la comparación es mecánica, no a ojo:

            · `doble_lectura_letras` — el pie lleva el total EN LETRAS
              ("SON: MIL CUATROCIENTOS VEINTE EUROS") y el NIF con otra
              puntuación, con guiones, frente al de la cabecera sin
              ellos. Mismo valor, notación distinta: **no se puede
              copiar del cuadro**. Si `nif_margen` vuelve con guiones,
              se ha leído el pie de verdad. Y de paso mide algo que no
              había medido nadie: si el modelo sabe leer un importe
              escrito con letras, que es como lo imprime media
              facturación española.
            · `doble_lectura_descuadre` — el pie lleva OTRO importe
              (1.120,00 frente a 1.210,00 del cuadro: dos dígitos
              permutados, que es el error de tecleo real y no uno
              inventado). Discriminación total para `total_factura_2`,
              y **el motor debería ponerse ROJO** — el guard de doble
              lectura nunca se ha visto disparar sobre un documento.
            · `con_retencion` — IRPF al 15%: el total NO es base + IVA.
              Un modelo que suma de memoria en vez de leer falla ahí y
              sólo ahí. Ejercita `irpf_retencion`, que el contrato
              declara y ninguna muestra había usado nunca.

          **El orden importa:** primero la `_limpia` de cada receta. Si
          la limpia ya falla, la degradada no añade información — el
          problema no es la foto. Sólo cuando la limpia acierta, la
          degradada mide de verdad cuánto aguanta, porque el documento
          es EL MISMO y la única variable que cambia es la foto.

          **Límite declarado, para que nadie lo lea de más:** la
          degradación simula giro, luz desigual, desenfoque, ruido y
          JPEG, pero **NO la perspectiva** (el papel en ángulo, con los
          márgenes en trapecio). Que la degradada pase no significa que
          una foto en ángulo pase: eso no se ha medido.

          **LO QUE EL MOTOR DICE DE CADA UNA — medido, no supuesto.** La
          verdad conocida se ha pasado por `evaluar_fila_v4` de verdad.
          Sabiéndolo de antemano, un veredicto distinto al pasar la
          IMAGEN señala a la lectura, no al motor:

            doble_lectura_descuadre  → **ROJO**, y por el guard correcto:
                `doble_lectura_total: el total difiere entre las dos
                ubicaciones leidas: 1210.0 vs 1120.0`. Primera vez que
                ese guard se ve disparar sobre un documento.
            doble_lectura_letras     → AMBAR
            con_retencion            → AMBAR

          Los dos AMBAR **no son un defecto**: la verdad conocida
          describe el DOCUMENTO, y `verificacion` —la confianza que el
          modelo declara sobre su propia lectura— no es una propiedad
          del papel, la pone la captura. Sin ella el motor dice
          NO_COMPROBADO y baja a AMBAR, que es lo que tiene que hacer.
          Al pasar la IMAGEN por Gemini ese campo sí vendrá.

          ⚠️ **Y un detalle de contrato que costó encontrar:**
          `irpf_retencion` va **EN NEGATIVO**. Lo pide así el prompt de
          `captura_orquestador.py` y `guard_cuadre_total` la SUMA
          (base + IVA + irpf + recargo). Con el signo cambiado el
          descuadre es de DOS VECES la retención: la primera versión de
          esta muestra lo escribía en positivo y el motor daba
          `total_calc=2720.0 decl=2120.0`. Si alguna vez ves ese patrón
          —un descuadre que es justo el doble de la retención— es el
          signo, no el motor.

          **Nota de cobertura, aparte:** `test_motor_veredicto.py` no
          tiene hoy ningún caso con retención distinta de 0 (los tres
          llevan `irpf_retencion: '0'`). Esa rama de `guard_cuadre_total`
          no la ejercita la suite del motor; la ejercita ahora
          `test_muestras_sinteticas.py`, pero conviene saberlo.

          ─────────────────────────────────────────────────────────────
          ✅ **Y LA COMPARACIÓN YA NO SE HACE A OJO (16-09-2026).**

              python captura_orquestador.py --imagen <muestra> \
                     --procedencia SINTETICO > captura.json
              python comparar_captura_vs_verdad.py captura.json

          Encuentra el `_verdad.json` solo, compara campo a campo con el
          parser del propio contrato (`1.420,00` y `1420.0` son el mismo
          dato), **contesta las cuatro preguntas del Paso 1 él solo**, y
          termina pasando lo que el modelo leyó por el motor.

          Códigos de salida, los tres de siempre: `0` todo comprobado y
          coincidiendo · `1` hay una diferencia real · `2` nada discrepa
          pero algún campo no vino — que **no es un aprobado**. Un "todo
          bien" que significa "no vino casi nada" era el peor resultado
          posible de comparar a ojo.

          Dos decisiones suyas que conviene conocer antes de usarlo:

            · **`nif_margen` NO se normaliza.** En la muestra de letras
              la puntuación ES la medición: quitar los guiones dejaría
              en verde justo el caso que se quiere cazar.
            · **Lo que no esté declarado SINTETICO se trata como REAL** y
              entonces no imprime ni un valor, ni el nombre de la
              muestra, ni la ruta del fichero — sólo coincide / no
              coincide / no vino. La medición se conserva entera; lo que
              desaparece es el dato. No hay forma de desactivarlo.

          ⚠️ **UN HALLAZGO QUE IMPORTA MÁS QUE LA HERRAMIENTA.** Al
          simular una lectura en ESPEJO —el modelo copia el total del
          cuadro en `total_factura_2` en vez de leer el pie— el motor
          da **VERDE**. Y es correcto que lo dé: ve dos totales iguales.

          Es decir: **el guard de doble lectura sólo vale si las dos
          lecturas son independientes de verdad.** Si el modelo copia,
          el guard no protege nada y además lo firma en verde. Eso no se
          arregla en el motor —él no puede saber de dónde salió el
          segundo número—: se arregla comprobándolo, y es exactamente lo
          que mide `doble_lectura_descuadre`. Por eso esa muestra es la
          más importante de las tres.

      **Y dos defectos reales encontrados en la primera ejecución contra
      la API de verdad — exactamente para eso servía este paso:**
        1. El PDF se enviaba etiquetado como `image/jpeg` (el mapa de
           `mime_type` en `leer_factura_gemini()` y `_leer_factura_claude()`
           no tenía `.pdf` y caía en un "por defecto" silencioso). Gemini
           lo rechazaba con "Unable to process input image". Arreglado en
           los dos sitios: extensión no reconocida ahora lanza error, no
           adivina. `audit_project.py` en 0 antes y después.
        2. `puerta_cloud.Lote.anotar_resultado()` existía desde el 16-09
           pero nadie la llamaba — el registro salía con tokens/coste en
           `null` a pesar de que el mecanismo estaba listo. Enganchado en
           `leer_factura()`, el punto único; confirmado con tokens reales:
           **1.562 entrada / 453 salida** por una factura. Con la tarifa
           pública de `gemini-3.1-flash-lite` (no verificada de forma
           oficial, solo orientativa): del orden de 0,001 $/factura.

      Punto (e) cumplido con dato real, no estimado: mira
      `registro_cloud.jsonl`, línea `"tipo": "RESULTADO"`.

      **Es lo mejor que puedes hacer, y no necesita DPA.** Pasa
      una factura FABRICADA por la cadena entera con Gemini de verdad.
      Valida la clave, el SDK, el prompt, la puerta, el registro de
      coste y el motor — con cero exposición legal. Cuando después
      llegue la factura real, el único dato nuevo será el dato.

        a) Activa facturación en Gemini y pon la clave:
               set GEMINI_API_KEY=...
               set OS_ASESORIA_CLOUD=1
           (NO pongas OS_ASESORIA_DATOS_REALES: no hace falta, y la
            puerta debe seguir bloqueando lo real hasta el paso 2)

        b) python crear_factura_sintetica.py
           Genera `factura_sintetica_01.html` e imprime la VERDAD
           CONOCIDA de ese documento. Ábrelo en el navegador y guárdalo
           como PDF o hazle una captura de pantalla.

        c) python captura_orquestador.py --imagen <la captura> \
               --procedencia SINTETICO

        d) COMPARA campo a campo contra la verdad que imprimió (b).
           Las cuatro preguntas que hay que contestar están ahí, y la
           primera es la que más importa:

             · ¿Viene `tramos_iva` con los DOS tramos, incluido el 5%?
               El 5% no tiene campo plano equivalente: si no llega por
               ahí, se pierde entero. Es el defecto que se encontró y
               arregló el 16-09 — esto lo prueba contra un modelo real.
             · ¿`total_factura_2` trae el total del PIE o ha copiado el
               del cuadro? Si lo copia, la doble lectura es un espejo.
             · ¿`nif_margen` trae el NIF del pie?
             · ¿El número sale como `A26/7.612`, con barra y punto?

        e) Mira `registro_cloud.jsonl`: ahí está el primer coste real
           medido del proyecto. €/documento deja de ser una estimación.

        SI FALLA LA LLAMADA, dónde mirar primero (declarado el 16-09
        porque desde Cloud no se pudo ejecutar: ni SDK ni clave):
          · Error de MODELO no encontrado → `gemini-3.1-flash-lite` se
            verificó vigente contra la documentación oficial el 16-09,
            pero los modelos se retiran. Es lo primero que caduca.
          · Error de FORMA de la petición → la llamada usa
            `types.Part.from_bytes(...)`, que es la forma documentada del
            SDK. Si tu versión de `google-genai` fuera antigua y no lo
            tuviera: `pip install -U google-genai`.
          · La puerta bloquea → `python puerta_cloud.py` dice por qué en
            una línea, y `python modo_trabajo.py` qué falta encender.

      ── PASO 2 · LA DECISIÓN DEL DPA ───────────────────────────────

      Son DOS decisiones, no una (ver punto 1 de EL ORDEN):
        [X] Google/Gemini con facturación activa — **HECHA 16-09-2026.**
          Tarjeta vinculada, prepago de 5 € completado, AI Studio confirma
          "Se activó el nivel pagado de la API de Gemini". Verificado
          contra los Términos Adicionales oficiales (`ai.google.dev/
          gemini-api/terms`, no un resumen de terceros): con cuenta de
          facturación activa, TODO el uso —incluido lo gratuito— cuenta
          como "Paid Service" a efectos de dato, y en Paid Service "Google
          doesn't use your prompts [...] to improve our products". El
          crédito de bienvenida de 300 $ NO cubre este cargo (excluido
          explícitamente para la API de Gemini/AI Studio); los 5 € los pagó
          la tarjeta. Google entra como SEGUNDO encargado del tratamiento,
          con su propio marco contractual — sigue sin resolver la base
          legal, informar a los clientes ni el secreto profesional, que
          siguen siendo del despacho (`.claude/rules/datos.md`).
        [ ] Anthropic, y SÓLO si algún día quieres la ruta 4 (que yo vea
          el documento original). Para el flujo normal no hace falta.

      ── PASO 3 · UNA FACTURA REAL, UNA SOLA ────────────────────────

        set OS_ASESORIA_DATOS_REALES=1
        python captura_orquestador.py --imagen factura.jpg \
            --procedencia REAL --confirmo-envio 1

      La confirmación es el RECUENTO EXACTO, no un "sí". Si no coincide
      con los documentos encontrados, la puerta bloquea.

      ── LO QUE NO HAY QUE HACER MAÑANA ─────────────────────────────

        · No construir el router ni presupuestos ni reintentos: sus
          constantes se miden con las primeras facturas (§5).
        · No construir `proyeccion_minima.py` hasta tener el primer CSV
          real delante (§5.A-bis).
        · No procesar un lote grande antes de que UNA factura haya ido
          de punta a punta. Es "Puerta 1 antes que Puerta 2", la regla
          que este proyecto ya ha violado cuatro veces.

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

          ⚠️ **PRECISIÓN 16-09-2026: son DOS decisiones, no una.** Si el
          OCR lo hace Gemini, hace falta también la vía de pago de Google
          con facturación activa (la capa gratuita de AI Studio entrena
          con tus datos). Google entra entonces como un SEGUNDO encargado
          del tratamiento, con su propio DPA — exactamente el mismo
          razonamiento que ya está escrito para Workspace en
          `.claude/rules/datos.md`. Dos proveedores en la cadena, no uno.

          ✅ **Lo técnico de esta puerta YA ESTÁ (16-09-2026)**, y está
          cerrado por defecto: `puerta_cloud.py`. Mientras la decisión no
          se tome, la puerta bloquea todo documento real — y permite
          ejercitar la cadena entera con documentos SINTÉTICOS declarados,
          que es todo lo que se puede avanzar sin cruzarla.

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
            - [~] Los **porcentajes de retención** que reconoce
              `guard_retencion_vs_error` — **CONTRASTADOS 15-09-2026
              (sesión Cloud), 5 de 6 cerrados, 1 pendiente de Diego.**
              `RETENCIONES_TIPICAS = [1, 2, 7, 15, 19, 21]`: el art. 74
              (ya citado) solo respalda que EXISTA la retención, no fija
              ningún número. Leídos los artículos que sí los fijan (texto
              vigente, `RD 439/2007`): **15%** y **7%** (art. 95.1,
              profesionales, general y inicio de actividad), **1%** y
              **2%** (art. 95.4-6, agrícola/ganadera — engorde porcino y
              avicultura al 1%, el resto al 2% — y estimación objetiva de
              ciertos epígrafes al 1%), **19%** (art. 100, arrendamiento
              urbano; art. 90, capital mobiliario general; art. 99,
              premios). Los cinco números tienen artículo vigente que los
              respalda para el periodo del corpus (2016-2026). Detalle
              completo en la nota de `autoridad_guards.py` (guard
              `guard_retencion_vs_error`).

              **El 21% queda declarado, no retirado.** No aparece en
              ninguno de esos artículos vigentes — el único precedente
              encontrado es que la retención general de profesionales y de
              capital mobiliario SÍ fue del 21% entre 2012 y 2014 (medida
              antidéficit, derogada por la reforma de 2015), **fuera del
              rango del corpus** (2016-2026). No se ha quitado de la lista
              sin preguntar: **¿lo has visto de verdad en alguna factura
              real del corpus, Diego?** Si no, se retira; si sí, se anota
              por qué sigue viva (quitarlo a ojo sería el mismo error que
              añadirlo a ojo).
            - El **RD 1514/2007 (PGC)** para el supuesto de inmovilizado
              de `guard_tipo_operacion_especial` sigue sin leerse: no
              tiene la misma estructura de articulado fiscal y merece su
              propia pasada.
            - [X] `nif_check.py` — **RESUELTO 15-09-2026 (sesión Cloud).**
              Exigía control-letra solo para `"PQSW"`; `triangulacion_
              identidad_v0.py` ya usaba `"PQRSNW"` desde antes — la misma
              regla, arreglada en un fichero y no en el otro. Contrastado
              contra la especificación técnica de la AEAT (tabla oficial
              "letra inicial y código de control según la forma jurídica",
              verificada en dos fuentes independientes, no adivinada):
              faltaban **R** (congregaciones e instituciones religiosas) y
              **N** (entidades extranjeras) en el grupo de control-solo-
              letra. Medido antes de tocar nada: un CIF sintético con letra
              R o N y control en dígito pasaba `OK` cuando debía ser
              `FALLO`. Arreglado; `diff_comportamiento_motor.py::cif_valido`
              (el generador de CIF de prueba "cuando toques el motor")
              actualizado igual, para que no se desincronice del mismo modo.
              Prueba nueva en `test_motor_veredicto.py` (construida por
              partes, sin dejar un literal con forma de NIF en el código —
              si no, salta `scripts/privacy_scan.py`, como ya casi pasa al
              escribirla). `test_motor_veredicto.py` y `test_adversarial.py`
              en verde antes y después (regla de `.claude/rules/
              contabilidad.md`).

              **Y de propina, el mismo agujero pero en la barrera de
              privacidad:** el patrón de CIF de `scripts/privacy_scan.py`
              tampoco incluía la `R` — mismo patrón de bug que el ya
              documentado y cerrado el 26-08 para `X/Y/Z` (prefijo de NIE).
              Un CIF real que empezara por R no se habría detectado.
              Verificado antes de tocar nada (mismos 7 dígitos y control:
              con letra N daba match, con R no). Arreglado, con prueba
              nueva en
              `test_privacidad.py` (`cebo_cif_r`, mismo estilo que
              `cebo_nie`); suite 30/30 → **31/31**. Escáner ejecutado sobre
              todo el repositorio tras el cambio: sin hallazgos.

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
  5 · LA CAPA DE ORQUESTACIÓN (el "router") — DECIDIDO EL ORDEN, NO EL DISEÑO
  ═════════════════════════════════════════════════════════════════════
      Abierto el 16-09-2026, de una propuesta de arquitectura de Diego
      (separar desarrollo de procesamiento real, Gemini como sensor, un
      router que decida qué modelo ve qué dato y cuánto cuesta).

      **El fondo se acepta entero, y una parte ya existía.** Medido en el
      repositorio antes de opinar, no supuesto:
        - Punto único de salida: `captura_orquestador.py` ya era el ÚNICO
          fichero que llamaba a una API. La capa estaba, sin defenderse.
        - Contrato de extracción rico (valor + confianza + segunda
          lectura): el prompt v2 ya pide `confianza_campos`,
          `total_factura_2`, `nif_margen`/`nombre_margen`. Ya estaba.
        - Gemini = sensor, motor = autoridad: ya era la arquitectura.

      **Lo que faltaba de verdad — y ya está hecho (16-09-2026):** que la
      puerta se NIEGUE por defecto, que deje CONSTANCIA, y que exista un
      auditor que impida una segunda salida en silencio. Ver
      `puerta_cloud.py`, `test_puerta_cloud.py` (50 comprobaciones, con
      controles negativos) y el auditor `check_salida_unica_cloud`.

      ─────────────────────────────────────────────────────────────────
      LO QUE SE DECIDIÓ **NO** CONSTRUIR TODAVÍA, Y POR QUÉ
      ─────────────────────────────────────────────────────────────────
      La propuesta incluía presupuesto por documento, circuito de
      reintentos, selección de modelo, escalado por confianza y una rama
      de OCR local para ahorrar llamadas. **Nada de eso se ha construido,
      a propósito**, y el motivo es el mismo que este proyecto ya tiene
      documentado cuatro veces: es Puerta 2 antes que Puerta 1.

        · Sus constantes no se pueden fijar hoy sin inventárselas. La
          propia propuesta usaba "60 / 25 / 15" como ejemplo de cuántas
          facturas traen texto extraíble. Ese número **se mide** con las
          93 fotos que ya están en el disco, no se estima.
        · La rama de OCR local es una falsa economía **y un riesgo**:
          obliga a validar DOS caminos de extracción, cada uno con su
          forma de equivocarse en silencio, para ahorrar céntimos sobre
          un proceso que hoy cuesta ~51 s de trabajo humano por factura.
          Optimizar el coste de API **antes de haberlo medido** es
          optimizar la variable equivocada.
        · Fijar umbrales a ojo es el error que ya está documentado en el
          `5` de `fase0_huella_cliente.py`, el `MIN_NIFS=3` (punto 1.E,
          todavía abierto) y el `1σ` de `importe_atipico`.

      **Lo que SÍ se congela ahora, porque es barato de fijar y caro de
      cambiar después:** las interfaces. `FacturaCanonica`, la firma de la
      puerta y `CAMPOS_REGISTRO`. La POLÍTICA (presupuestos, umbrales,
      reintentos, qué proveedor) se queda deliberadamente sin congelar:
      es justo lo que los datos tienen que decidir.

      ✅ **SABER EN QUÉ MODO ESTAMOS — HECHO 16-09-2026.** Petición de
      Diego, y era la pieza que faltaba para trabajar sin preguntar:
      `python modo_trabajo.py` dice, **medido en el momento**, en qué
      superficie estamos, qué llaves hay puestas (sólo si están, nunca su
      valor), qué puede ver Claude, y para cada tarea concreta si se puede
      hacer AHORA o qué falta encender. Un resumen sale en cada
      `arranque.py`, así que está delante sin que nadie se acuerde.
      Las **cuatro rutas** de datos quedan ordenadas de menos a más
      exposición, y ese orden ES la política: no se usa una ruta más
      expuesta si una anterior resuelve lo mismo.

      [ ] A-bis · **LA RUTA 3, QUE ES LA QUE FALTA POR CONSTRUIR**
          (`proyeccion_minima.py`). De lo que Gemini extraiga se construye
          EN LOCAL una proyección sin identidad —sin NIF, sin razón
          social, sin ruta— y ESO es lo que Claude ve para analizar un
          caso. Es la que permite seguir trabajando como aquí sobre
          facturas reales **sin que la factura viaje**.
          **Disparador acordado: el primer CSV real.** No antes —
          construir la proyección sin un CSV delante es decidir a ojo qué
          campos hacen falta, y ya sabemos cómo acaba eso. `modo_trabajo.py`
          la declara como NO construida, y lo seguirá diciendo hasta que
          el fichero exista: no es un olvido, es un pendiente visible.

      [ ] A · MEDIR ANTES DE ROUTEAR. Cuando pasen la primera factura y
          el primer lote, el registro de la puerta ya da €/documento,
          tokens y tasa de bloqueo sin trabajo extra. Con eso —y no
          antes— se construyen solo las piezas del router que los números
          pidan. Es probable que la mitad se caigan por innecesarias.

      [ ] B · UNA MÉTRICA MEJOR QUE LA PRECISIÓN DEL OCR, y conviene
          fijarla de antemano: **cobertura de automatización segura** —
          qué fracción de documentos llega de la imagen al asiento sin
          intervención humana y con error residual aceptable. Un OCR del
          99,9% con errores semánticos peligrosos es peor que uno del
          99,5% que sabe decir NO_COMPROBADO. Encaja con lo que el
          proyecto ya decidió que es LA métrica (falsos verdes).

      [ ] C · UNA DISTINCIÓN QUE SÍ MERECE ENTRAR AL MOTOR cuando haya
          casos: más OCR **no arregla** una ambigüedad fiscal. Un
          timeout o un JSON truncado se reintentan; un "IVA 0%" que puede
          ser exenta, no sujeta o ISP **no se reintenta**, se manda a
          revisión. Hoy el motor ya lo trata así (`naturaleza_operacion`);
          lo que falta es que el futuro router no lo desaprenda.

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
