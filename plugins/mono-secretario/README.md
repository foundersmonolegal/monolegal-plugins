# Mono Secretario

Ordena el desorden de un caso y lo guarda en la memoria del mono (Mono Virtual) para que el cliente lo vea en su app. Con un solo comando, Claude lee la carpeta del caso, el WhatsApp con el cliente y, si está conectado, el correo. Después le cuenta al abogado **en qué fase está el caso y cuál es el siguiente paso**: qué hay que hacer, a quién le toca y el plazo que fija la resolución. Lo acompaña de un resumen de la historia del caso y de las fuentes de las que sale. El abogado lo revisa y lo corrige en una página antes de guardarlo.

Alcance de esta versión: España, Comunitat Valenciana. Un caso por ejecución.

## Para empezar

Instala el plugin y escribe `/mono-secretario:inicia` en una tarea de Cowork. El mono comprueba que todo está conectado y abre la guía en el panel.

## Cómo se usa

1. Instala el plugin desde el marketplace de Monolegal (repositorio de GitHub `foundersmonolegal/monolegal-plugins`):
   - **Cowork:** en Customize > Plugins, añade ese marketplace e instala **Mono Secretario**.
   - **Claude Code:** `claude plugin marketplace add foundersmonolegal/monolegal-plugins` y después `claude plugin install mono-secretario@monolegal`.
   - Si no puedes usar GitHub: **Customize > Plugins > Add > Upload plugin** con `mono-secretario.zip`.
2. En la pestaña **Connectors** del plugin, conecta **Mono Virtual** con tu cuenta de Monolegal. Si pide un identificador de cliente, escribe `claude`.
3. Opcional: conecta **Gmail** en Customize > Connectors. Si la ficha lo permite, deja activas solo las herramientas de lectura.
4. Exporta el chat de WhatsApp con el cliente a la carpeta del caso: *Exportar chat › Sin archivos*. Si usas dos teléfonos, exporta un chat por cada uno.
5. Abre una tarea de Cowork con la carpeta del caso conectada y escribe `/mono-secretario:ordenar-caso` o "ordena este caso".
6. Dile a Claude el nombre del cliente. No hace falta el número del caso.
7. Revisa la página del panel, pulsa **Confirmar y copiar para Claude** y pega el resultado en el chat. El mono lo guarda y te lo confirma en el panel.
8. Cuando el caso queda guardado, el mono te ofrece enviar a tu cliente el acceso a su caso en el móvil. También puedes pedirlo en cualquier momento: "envía el acceso a mi cliente del caso X" (`enviar-acceso`). El mono te propone el correo del cliente y no envía nada hasta que lo confirmas. Después pulsa **Compartir por WhatsApp** en el panel para mandarle también el enlace y el código.

## Qué hace por dentro

- Se lista la carpeta del caso (también si está en Google Drive) sin abrir nada, un script elige los documentos que hay que leer y solo esos se traen. Otro script recorre esos documentos y los chats exportados, identifica el caso por su NIG, descarta jurisprudencia, normativa y documentos de otros casos, y ordena los documentos por su fecha real: la de notificación de LexNET o la de la resolución, no la de modificación del archivo.
- Antes de que nada salga del equipo, sustituye los datos personales de documentos y WhatsApp por claves (`[CLIENTE]`, `[DNI_1]`, `[TEL_1]`…). La tabla con los valores reales se queda en `.monolegal/datos_personales.json`.
- Un subagente de solo lectura lee los documentos más recientes, los últimos mensajes de WhatsApp y los correos con el cliente y con el procurador, y devuelve hechos con su cita literal.
- Claude sitúa el caso en el mapa de fases de su tipo de proceso y toma el siguiente paso del pie de recursos de la última resolución. No calcula plazos.
- Al confirmar, un script prepara las llamadas al MCP de casos: fechas con la zona de Madrid, un código de cliente estable sin datos personales y ningún texto con claves de datos personales. Después Claude crea el caso, registra las actuaciones y el estado, muestra la confirmación y envía los tiempos de la ejecución (`registrar_ejecucion`).
- Para enviar el acceso al cliente (`enviar-acceso`), Claude decide con los hechos anonimizados cuál de las claves `[EMAIL_n]` es la del cliente y `correo_cliente.py` le da, en tu equipo, el correo real de esa clave y de ninguna otra. Tú lo confirmas antes de que `enviar_codigo_acceso` envíe el correo con el enlace y el código; Claude nunca envía una clave al MCP ni inventa un correo.

Deja sus archivos de trabajo en la subcarpeta `.monolegal/` del caso.

## Datos

- Documentos y WhatsApp: a Claude solo le llegan con claves en lugar de nombres, DNI/NIE, teléfonos, correos, IBAN y direcciones. La detección cubre las personas conocidas (cliente, partes de las cabeceras, interlocutores del WhatsApp), las que van tras un tratamiento (D., Dña., Sr., Sra.) y los datos con formato fijo; un nombre que solo aparezca suelto en un texto puede escaparse.
- Correo: Claude lo lee **sin anonimizar**, con herramientas de solo lectura. Nunca envía, responde ni borra correos.
- A la memoria del mono (`Mono_Virtual`, `https://api.aiworkforce.monolegal.com/mcp`) llegan el nombre del cliente, que es lo que muestra la app, y lo que el abogado confirma, escrito para el cliente y sin otros datos personales. También llegan los tiempos y las cifras de cada ejecución. Si pides enviar el acceso, llega además el correo de tu cliente que tú confirmas, y se guarda con su código de acceso.

## Actualizar

Las versiones nuevas se publican en el mismo marketplace. En Claude Code, actualiza con `claude plugin update mono-secretario@monolegal` o activa la actualización automática del marketplace en `/plugin` > Marketplaces (en los marketplaces de terceros viene desactivada). Con el zip no hay actualizaciones: hay que volver a subirlo.

## Legal

- [Política de privacidad](https://app.monosvirtuales.monolegal.com/privacidad), [términos y condiciones](https://app.monosvirtuales.monolegal.com/terminos), [acuerdo de tratamiento de datos](https://app.monosvirtuales.monolegal.com/acuerdo-tratamiento) y [soporte](https://app.monosvirtuales.monolegal.com/soporte).
- Licencia propietaria, todos los derechos reservados: ver [LICENSE](LICENSE).

## Desarrollo

Tests: `python -m unittest discover -s plugins/mono-secretario/tests`. Empaquetar: `python plugins/empaquetar.py plugins/mono-secretario`.
