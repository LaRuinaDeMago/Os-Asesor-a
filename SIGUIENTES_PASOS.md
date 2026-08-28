# Siguientes pasos — qué hacer, en qué orden, y qué decidir con cada número

> Escrito el 21-08-2026, al final de una sesión cloud de verificación. No es una
> lista de tareas: es una **estructura de decisión**. La diferencia importa,
> porque el proyecto lleva un mes produciendo trabajo y cero números, y una lista
> de tareas más no arregla eso.

---

## 1. Dónde está el proyecto, en un párrafo honesto

El motor está verificado a un nivel poco habitual: 108 ataques adversariales,
1.786 mutaciones mecánicas sobre facturas VERDE sin un solo escape sin explicar,
26/26 guards con cobertura útil, ninguna rama muerta, ningún guard mudo, la
cadena entera ensayada de punta a punta y once defectos reales cerrados en un
día. La barrera de privacidad tiene por fin su propia batería.

**Y no hay ni un solo número real.** Todo lo medido sale de corpus fabricados.
Eso no es un fracaso del trabajo hecho —hacía falta, y ha encontrado cosas
graves— pero sí es el hecho más importante del proyecto ahora mismo, y conviene
no disfrazarlo: **un motor perfectamente verificado contra datos inventados sigue
siendo una hipótesis.**

---

## 2. Qué está bloqueado por qué — y la sorpresa

| Lo que falta | Bloqueado por | ¿Cuesta dinero? |
|---|---|---|
| Tasa de falsos rojos sobre el histórico | **nada** | no |
| Falsos verdes sobre las 91 facturas de la prueba antigua | **encontrar el fichero** | no |
| Cuadre contra el 303 presentado | **localizar los modelos** | no |
| Captura real (foto → JSON) | DPA + API contratada | sí |
| Todo `DIRECCION_PRODUCTO.md` | DPA | sí |

> **La sorpresa es que las tres primeras no están bloqueadas por nada.** No
> esperan al DPA, ni a Workspace, ni a Gemini, ni a terminar el inventario. Solo
> esperan a estar sentado delante del PC de la asesoría con la ruta del corpus.
>
> Eso es lo que hay que hacer primero, y no porque sea lo más ambicioso: porque
> es lo único que puede convertir un mes de hipótesis en un hecho.

---

## 3. Las tres mediciones libres, en orden — y por qué ese orden

El orden **no es por valor**. Es por *qué descarta cada una* y *qué cuesta
equivocarse*. Se ordena para que, si algo va mal, se sepa lo antes posible y lo
más barato posible.

### 3.1 · Primero: el retro-semáforo (una hora)

```bash
python retro_semaforo.py "RUTA_DEL_CORPUS" --limite 2000    # primera pasada
python retro_semaforo.py "RUTA_DEL_CORPUS" --inyectar       # la completa
```

**Va primero porque es lo único que puede decir «esto no sirve» en una hora.**
Si el motor marca ROJO al 40% de asientos que en su día se contabilizaron y se
presentaron, todo lo demás es discutir el color de una pared que hay que tirar.

| Puede decir | No puede decir |
|---|---|
| Falsos rojos (¿molesta?) | **Falsos verdes.** Que un asiento se contabilizara así demuestra que se hizo así, no que fuera correcto |
| Dónde está el ruido (qué guards saltan) | Nada sobre la captura por IA |
| Tasa de detección con `--inyectar` (¿sirve?) | Nada sobre deducibilidad |

> ⚠️ **Leer el ÁMBAR con cuidado, y esto es nuevo.** El script ahora separa el
> ámbar *del instrumento* del ámbar *de la factura*. Sobre corpus sintético salía
> **51,04% ámbar** y el atribuible a las facturas era **0,0%**: todo era el
> instrumento (el diario no trae el NIF del titular, y el maestro se acumula
> sobre la marcha). **Mirar la segunda cifra, no la primera.**

### 3.2 · Después: las 91 facturas fotografiadas (una tarde)

```bash
python validar_captura_historica.py "ruta/al/fichero.csv" --columna-humano CORRECTO \
    --nif-titular "NIF_DEL_CLIENTE" --ejercicio 2026
```

**Va segunda porque es lo único que puede hablar de FALSOS VERDES**, que es
exactamente lo que el retro-semáforo no puede tocar por construcción. Es el único
material del proyecto que ha recorrido la cadena entera —papel, cámara, lectura,
motor— con datos de verdad.

Y si nadie anotó el veredicto humano, **sigue habiendo premio**: el script dice
qué facturas cambian de veredicto entre el motor de entonces y el de hoy. Eso
convierte *«revisar 91»* en *«revisar las 12 que han cambiado»*.

> **Qué esperar, para no confundir un resultado con un fallo:** si el fichero
> trae base/IVA/total pero no el desglose por tipos, las del 21% y del 0% saldrán
> VERDE o ROJO, y **las de tipos intermedios saldrán ÁMBAR `[FALTA DATO]`**
> pidiendo el desglose. Eso no es el motor fallando: es el motor negándose a
> afirmar una composición que no puede comprobar. Si salen muchas, lo que dice es
> que **la captura tiene que emitir `tramos_iva`**.

### 3.3 · Y luego: el cuadre contra el 303 (varias sesiones)

```bash
python reconstruir_303.py "RUTA_DEL_CORPUS" --detalle 303_LOCAL.json
```

**Va tercera porque es la más lenta y la que más depende de encontrar cosas** —
los modelos presentados están fuera de la carpeta de contabilidad—, no porque
valga menos. Al contrario: **es la única verdad externa que este proyecto va a
tener nunca.** Todo lo demás se valida contra sí mismo.

Si las casillas 01-09 y 28-29 cuadran durante cuarenta trimestres, lo validado no
es una factura: es **la cadena entera de lectura** contra algo que Hacienda ya dio
por bueno.

---

## 4. La parte que casi nadie hace: decidir el umbral ANTES

Un número sin un umbral acordado de antemano no decide nada — se racionaliza. Si
sale mal, siempre hay una explicación a mano; si sale bien, siempre parece que ya
se sabía. **Estos umbrales se acuerdan ahora, antes de ver ningún número.**

| Medición | Si sale... | Entonces |
|---|---|---|
| **Falsos rojos** (retro) | **> 15%** | El motor molesta más de lo que ayuda. Se para todo lo demás y se trabaja en el ruido: el informe dice qué guards saltan |
| | 5–15% | Utilizable con revisión. Se mira qué guards concentran el ruido y se afinan esos |
| | **< 5%** | Verde. Se pasa a la 3.2 sin tocar el motor |
| **Detección** (`--inyectar`) | **< 70%** | El motor no caza los errores que se cometen de verdad. Es el problema, no la captura |
| | 70–90% | Suficiente para asistir, no para automatizar |
| | **> 90%** | El cuello de botella está en la captura, no en el motor |
| **Falsos verdes** (91 facturas) | **≥ 1 falso verde** | **Se para la automatización.** Un falso verde con datos reales vale más que mil pruebas sintéticas en verde. Se estudia caso por caso antes de seguir |
| | 0 sobre ≥ 30 juzgadas | Evidencia real, pero **n pequeña**: no se convierte en «el motor no da falsos verdes», se convierte en «no hemos visto ninguno en 30» |
| **Cuadre 303** | 1 trimestre no cuadra | Se investiga ese. No se ajusta nada para que cuadre |
| | > 10% no cuadran | La reconstrucción tiene un fallo sistemático. Se busca el patrón, no se parchean casos |

> **La regla que hay detrás de toda la tabla:** el número decide, no la
> expectativa. Si sale mal, sale mal — y saberlo en una hora es exactamente para
> lo que se ha construido todo esto.

---

## 5. Lo que el DPA desbloquea, y lo que no

Repetido aquí a propósito porque es fácil leerlo como «con el DPA ya se puede
todo» (está desarrollado en `.claude/rules/datos.md`):

- **Desbloquea:** que el modelo LEA una factura de un cliente. Es decir, toda la
  captura real, y con ella toda `DIRECCION_PRODUCTO.md`.
- **No desbloquea nada de la sección 3.** Las tres mediciones libres funcionan con
  el diseño de tres roles y no necesitan DPA: Claude escribe el script, Diego lo
  ejecuta, Claude lee solo recuentos. El dato no viaja.
- **No sustituye** la base legal, la minimización, informar a los clientes ni el
  secreto profesional. Un DPA hace **legal** el viaje; **no viajar sigue siendo
  más fuerte que viajar con contrato.**

> Y de ahí sale el orden económico obvio: **no se contrata nada hasta tener el
> número de la sección 3.1.** Si el motor molesta al 40%, el DPA no arregla eso y
> el dinero se ha gastado antes de saberlo.

---

## 6. La trampa

Después de un día de encontrar once defectos, la tentación es seguir buscando
defectos. **Es una trampa**, y conviene decirlo aquí porque va a aparecer.

Los once salieron de mirar **las costuras** —entre una pieza y la siguiente—, y
esas costuras ya están recorridas: quedan ensayadas, con batería propia, dentro
de `audit_project.py`. Lo que queda por descubrir ya no está en el código: está
en los datos, y el código no puede contarlo.

> **La siguiente hora de trabajo más valiosa del proyecto no es escribir nada.
> Es abrir un terminal en el PC de la asesoría y ejecutar una línea.**

---

## 7. Y una cosa que no es código y sigue abierta

De `EMPEZAR_AQUI.md` §7, sin resolver y sin depender de nadie:

- Cifrar el USB de copia de seguridad.
- Guardar la clave de recuperación **fuera** de la máquina.
- Confirmar qué hay dentro de esa copia.

No es glamuroso y es lo único de esta lista que, si falla, no se puede rehacer.
