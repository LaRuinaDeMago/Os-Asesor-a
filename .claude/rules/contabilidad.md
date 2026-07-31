# Regla de contabilidad

Nunca modificar motor_veredicto.py (ni layout_diario_contaplus.py, orquestador.py,
que dependen de él) sin ejecutar test_motor_veredicto.py antes (para saber de qué
partes se parte) y después (para confirmar que sigue en verde).

Un guard nunca debe dar OK por omisión — si falta el dato para comprobar algo,
el estado es NO_COMPROBADO o NO_APLICA, nunca un OK silencioso.

Cualquier guard nuevo que dependa de un caso real concreto (no sintético) debe
declararlo en su docstring como "caso real anonimizado" o "cliente piloto" —
nunca con el nombre real del cliente/proveedor, aunque el archivo se vaya a
quedar en local y nunca suba a GitHub. Es más fácil mantener la disciplina si
es constante en todo el código, en vez de decidir caso a caso qué archivo
"seguro que no sale de aquí".
