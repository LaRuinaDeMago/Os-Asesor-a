# archivo/ — sondas de la Fase 0 y diagnósticos de agosto

**Qué hay aquí.** 18 scripts que se escribieron entre el 11 y el 26 de agosto de
2026 para MEDIR el corpus real (`.DAT` de ContaPlus) y averiguar cómo estaba
hecho: cuántos contenedores había, dónde vivía la identidad del cliente, qué
campos estaban rellenos y cuáles no, qué formato tenían los importes. De ahí
salieron las cifras de `FASE0_RESULTADOS.md`.

**Por qué están aquí y no en la raíz.** Creado el 15-09-2026, en el repaso de
limpieza. Antes de moverlos se comprobó, uno por uno y con el código en la mano,
que los 18 cumplen las tres condiciones a la vez:

1. **Ningún otro `.py` los importa.**
2. **Ninguna documentación los nombra**, ni con `.py` ni sin él (se buscó en
   todos los `.md` de la raíz y en `.claude/`).
3. **Todos tienen `__main__`**: son scripts sueltos que se ejecutaban a mano,
   nunca módulos de los que dependa nada.

Es decir: no se ha roto ninguna dependencia al moverlos, porque no había
ninguna. La raíz pasó de 105 a 87 `.py`, y los 87 que quedan son código vivo.

---

## ⚠️ Lo que hay que saber ANTES de volver a ejecutar cualquiera de estos

**No son código vigente. Son el registro de cómo se llegó a lo que sabemos hoy.**

Varias de las premisas sobre las que se escribieron han sido **corregidas
después**, y la corrección no está dentro de estos ficheros — está en la
documentación que sí se mantiene. Los cuatro errores documentados del proyecto
(ver `ARQUITECTURA_DATOS.md` §4 y la corrección `⚠️ SUPERADO` de
`FASE0_RESULTADOS.md` §14-bis) son exactamente de esta época y de este tipo:

- `reconstruir_303.py` contaba dos veces lo que aparecía en varias copias.
- `cuenta_proveedor` se truncaba a 3 dígitos y fusionaba proveedores distintos.
- `clave_cliente()` usaba sólo la carpeta, cuando **una carpeta de ContaPlus
  puede tener hasta 70 empresas dentro**.
- La identificación de cliente por "huella" de contrapartes no se sostuvo.

> **Regla al usarlos:** sirven para entender **por qué** el proyecto decidió lo
> que decidió, y para reproducir una medición concreta si hace falta volver a
> ella. **No sirven como fuente de verdad sobre el estado actual.** Si un número
> de aquí contradice a `PROJECT_STATUS.md` o a los tests, mandan los tests
> (`CLAUDE.md`, jerarquía de verdad: Código → Tests → Git → PROJECT_STATUS.md).

**No se borran** justamente por eso: borrarlos dejaría `FASE0_RESULTADOS.md`
lleno de cifras sin nada detrás que explique cómo se obtuvieron.

---

## Siguen bajo todas las reglas del proyecto

Archivar no los saca de ninguna barrera, y conviene decirlo porque es fácil
suponer lo contrario:

- **Siguen tocando datos reales.** Casi todos reciben la ruta del corpus como
  argumento. Se aplica igual `.claude/rules/datos.md`: los ejecuta Diego en su
  máquina, y a la conversación sólo llegan recuentos — nunca un NIF, un nombre
  ni una ruta.
- **Siguen auditados.** `audit_project.py` recorre el repositorio con `rglob`,
  así que las comprobaciones de encoding, de suites y de importabilidad los
  siguen cubriendo aquí dentro exactamente igual que en la raíz. Archivar no
  es dejar de mirar.

---

## Un detalle que salió en el mismo repaso, y que no es de esta carpeta

`diag_formato_303_local.py` **se quedó en la raíz a propósito**: no está en el
repositorio. `.gitignore` lo excluye por la regla `*_local.*`, así que vive
sólo en el PC de la asesoría y nunca ha subido a GitHub. No se movió para no
tocar un fichero que está fuera del contrato del repositorio — pero queda
anotado aquí porque, mirando `ls *.py`, nada permite distinguirlo del resto.
