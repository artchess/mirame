# Seguridad

## Versiones con soporte

Se corrigen los problemas de seguridad en la última versión publicada. Mientras el proyecto esté en 0.x no se mantienen ramas anteriores: la corrección sale en una versión nueva.

## Cómo reportar una vulnerabilidad

No abras un *issue* público. Repórtala en privado desde [Security → Report a vulnerability](https://github.com/jacomv/mirame/security/advisories/new) e incluye:

- qué versión usas y en qué sistema operativo;
- los pasos para reproducirla;
- qué podría hacer alguien que la aproveche.

Recibirás respuesta en un máximo de siete días. Cuando la corrección esté publicada, el aviso se hace público y se da crédito a quien la reportó, si así lo quiere.

## Qué cuida Mírame

- La app escucha solo en `127.0.0.1` y rechaza peticiones que vienen de otros sitios abiertos en el mismo navegador.
- Las claves de IA se guardan en `configuracion.json` con permisos de lectura solo para el usuario (0600) y se muestran enmascaradas en la interfaz.
- El video no sale de la computadora. Con las claves de IA activadas se envía el audio al servicio de transcripción y el texto transcrito al modelo que marca las lecturas.
