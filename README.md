# Plugins de Monolegal para Claude

Este repositorio es el marketplace de Monolegal: desde aquí se instalan sus plugins para Claude (Cowork y Claude Code) y se reciben sus versiones nuevas.

## Plugins

- **[Mono Secretario](plugins/mono-secretario)** (`mono-secretario`): ordena el desorden de un caso, te muestra en qué fase está y cuál es el siguiente paso, y, cuando lo confirmas, se lo enseña a tu cliente en la app Mono Virtual.

## Instalar

- **Cowork:** en Customize > Plugins, añade el marketplace `Monolegal/monolegal-plugins` e instala el plugin.
- **Claude Code:**

  ```
  claude plugin marketplace add Monolegal/monolegal-plugins
  claude plugin install mono-secretario@monolegal
  ```

Después escribe `/mono-secretario:inicia` en una tarea: el plugin comprueba que todo está conectado y te guía paso a paso.

## Actualizar

En Claude Code, `claude plugin update mono-secretario@monolegal`, o activa la actualización automática del marketplace en `/plugin` > Marketplaces.

## Soporte y legal

[Soporte](https://app.monosvirtuales.monolegal.com/soporte) · [Privacidad](https://app.monosvirtuales.monolegal.com/privacidad) · [Términos](https://app.monosvirtuales.monolegal.com/terminos) · [Acuerdo de tratamiento de datos](https://app.monosvirtuales.monolegal.com/acuerdo-tratamiento)

Este repositorio se genera desde el repositorio interno de Monolegal: no se aceptan cambios directos. Cada plugin tiene su propia licencia (propietaria, todos los derechos reservados).
