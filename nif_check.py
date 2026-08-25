def valida_nif(nif):
    if not nif or not nif.strip():
        return (None, "SIN_DATO", "no hay NIF capturado")
    nif = nif.upper().replace(" ", "").replace("-", "").replace(".", "")
    # CORREGIDO 25-08-2026 (ver diag_campo_nif_origen.py, caso real
    # anonimizado sobre contabilidad historica): un campo de 1-2 caracteres
    # no es "un NIF invalido" -- no hay forma de que sea NINGUN formato real,
    # el mas corto (DNI/CIF/NIE) son 9. Verificado sobre el corpus real: en
    # el 100% de los 196 casos de longitud 1 encontrados, la linea de
    # ACREEDOR (donde vive el NIF de verdad) tambien estaba vacia -- no es
    # que el reconstructor mirara la linea equivocada, es que el dato nunca
    # se capturo (tipico de tickets/compras menores sin factura completa).
    # Declararlo FALLO ("hay un NIF y esta mal") es el mismo error que el
    # "OK por omision" que este proyecto prohibe, en sentido inverso: aqui no
    # hay NIF que evaluar.
    if len(nif) <= 2:
        return (None, "SIN_DATO", "el campo tiene contenido pero es demasiado corto para ser un NIF/CIF/NIE real")
    # NIF/CIF INCOMPLETO, no invalido (25-08-2026, ver diag_nif_otro_residual.py,
    # caso real anonimizado). Una cadena de longitud 8 con la FORMA exacta de
    # un DNI o un CIF a los que les falta solo el ULTIMO caracter -- el propio
    # digito de control -- no es un NIF que este mal: es un NIF al que le
    # falta precisamente el unico caracter que permite comprobarlo. Declararlo
    # FALLO ("esta mal") inventa un error que no se puede demostrar; es el
    # mismo principio que el campo de 1-2 caracteres de arriba, un escalon mas
    # arriba en longitud.
    #
    # Medido sobre el residuo "OTRO" de nif_digito_control: de 36 casos de
    # longitud 8, 34 (94%) tenian esta forma exacta -- 26 letra+7digitos (CIF
    # sin su digito de control) y 8 todo-digitos (DNI sin su letra de
    # control). Solo 2 no encajaban en ninguna de las dos formas y se quedan
    # fuera de este arreglo, sin inventarles una explicacion.
    if len(nif) == 8:
        if nif.isdigit():
            return (None, "SIN_DATO",
                    "8 digitos: forma de DNI al que le falta la letra de control, no verificable")
        if nif[0].isalpha() and nif[1:8].isdigit():
            return (None, "SIN_DATO",
                    "letra+7 digitos: forma de CIF al que le falta el digito de control, no verificable")
    letras_dni = "TRWAGMYFPDXBNJZSQVHLCKE"
    if len(nif) == 9 and nif[:8].isdigit() and nif[8].isalpha():
        num = int(nif[:8])
        letra_calc = letras_dni[num % 23]
        return (letra_calc == nif[8], "DNI", f"letra esperada {letra_calc}")
    # NIE (25-08-2026, ver diag_nif.py, caso real anonimizado): un extranjero
    # residente en Espana se identifica con X/Y/Z + 7 digitos + letra -- la
    # MISMA forma estructural que un CIF (letra + 7 digitos + control), asi
    # que sin esta rama especifica un NIE caia en la rama CIF de abajo y se
    # validaba con el algoritmo DE CIF, que no es el suyo (case rarisimo que
    # coincida por casualidad). Medido: 9 NIE reales marcados FALLO por
    # aplicarles el checksum equivocado. Ninguna letra de organizacion de CIF
    # empieza por X, Y o Z, asi que esta rama nunca le roba un caso a un CIF
    # autentico -- comprobar X/Y/Z primero es seguro.
    if len(nif) == 9 and nif[0] in "XYZ" and nif[1:8].isdigit():
        num = int(str("XYZ".index(nif[0])) + nif[1:8])
        letra_calc = letras_dni[num % 23]
        return (letra_calc == nif[8], "NIE", f"letra esperada {letra_calc}")
    if len(nif) == 9 and nif[0].isalpha() and nif[1:8].isdigit():
        letra_org = nif[0]; digitos = nif[1:8]; control = nif[8]
        suma_par = sum(int(d) for i, d in enumerate(digitos) if i % 2 == 1)
        suma_impar = 0
        for i, d in enumerate(digitos):
            if i % 2 == 0:
                doble = int(d) * 2
                suma_impar += doble // 10 + doble % 10
        total = suma_par + suma_impar
        digito_control = (10 - (total % 10)) % 10
        letras_cif = "JABCDEFGHI"
        if letra_org in "PQSW":
            ok = control == letras_cif[digito_control]
        elif letra_org in "ABEH":
            ok = control == str(digito_control)
        else:
            ok = (control == str(digito_control)) or (control == letras_cif[digito_control])
        return (ok, "CIF", f"digito esperado {digito_control}")
    # NIF-IVA extranjero (25-08-2026, ver diag_nif.py): un proveedor
    # intracomunitario se identifica con un prefijo de pais (2 letras) mas un
    # numero cuyo formato varia por pais miembro -- no hay un digito de
    # control unico que este motor pueda calcular sin consultar VIES (la
    # base de datos de la UE), y no hay una lista cerrada de paises que
    # merezca la pena mantener aqui: se probo con una lista explicita y el
    # 66% de los casos reales eran de paises fuera de ella. Fingir que "no
    # reconocido" equivale a "esta mal" seria un FALLO por omision -- el
    # mismo error que el "OK por omision" que este proyecto prohibe, en
    # sentido inverso. Se reconoce el FORMATO (2 letras + alfanumerico) y se
    # declara NO_COMPROBADO, nunca OK ni FALLO: no se ha verificado, y no se
    # finge lo contrario en ningun sentido.
    if 4 <= len(nif) <= 14 and nif[:2].isalpha() and nif[2:].isalnum():
        return (None, "NIF_IVA_UE", "formato de NIF-IVA extranjero reconocido; el digito de control no se puede verificar sin VIES")
    return (False, "DESCONOCIDO", "formato no reconocido")
