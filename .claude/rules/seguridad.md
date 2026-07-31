# Credenciales y tokens

Ninguna clave de API (ANTHROPIC_API_KEY, GEMINI_API_KEY) se escribe nunca dentro
de un archivo de código ni se pega en una conversación de chat. Se configuran
como variable de entorno en la máquina donde se ejecuta.

# Instalación de software en el equipo

No instalar software (intérpretes, paquetes, herramientas de sistema) sin
aprobación explícita del usuario para esa instalación concreta — es una
modificación del sistema, no una acción reversible sobre el proyecto. Preferir,
cuando exista, una alternativa portátil que no requiera privilegios ni modifique
el sistema (p.ej. la distribución "embeddable" de Python en vez del instalador
MSI, si el instalador falla o no hay privilegios).
