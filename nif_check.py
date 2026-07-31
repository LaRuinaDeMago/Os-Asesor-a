def valida_nif(nif):
    if not nif or not nif.strip():
        return (None, "SIN_DATO", "no hay NIF capturado")
    nif = nif.upper().replace(" ", "").replace("-", "").replace(".", "")
    letras_dni = "TRWAGMYFPDXBNJZSQVHLCKE"
    if len(nif) == 9 and nif[:8].isdigit() and nif[8].isalpha():
        num = int(nif[:8])
        letra_calc = letras_dni[num % 23]
        return (letra_calc == nif[8], "DNI", f"letra esperada {letra_calc}")
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
    return (False, "DESCONOCIDO", "formato no reconocido")
