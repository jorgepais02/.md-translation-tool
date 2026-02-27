# Killing the Kill-Chain (V): Caso práctico y recomendaciones finales

## Caso práctico: Compromiso completo de un Directorio Activo

Se presenta un escenario real basado en auditorías internas que ilustra una Kill Chain completa en un entorno Windows con Active Directory.

La infraestructura se segmenta en:

- Red del atacante.
- Red de estaciones de trabajo.
- Red de servidores.

### Acceso inicial

El atacante obtiene credenciales filtradas o adquiridas en mercados ilegales. Comprueba su validez y accede a la VPN corporativa como usuario de dominio sin privilegios.

### Escalada de privilegios local

Ya dentro de la red de estaciones de trabajo, el objetivo es obtener privilegios de administrador local. Posibles vectores:

- Acceso físico a un equipo sin disco cifrado.
- Explotación de vulnerabilidades locales.
- Descubrimiento de contraseñas almacenadas de forma insegura.

Una vez alcanzado el rol de administrador local, puede acceder a información sensible del sistema.

### Movimiento lateral hacia servidores

El atacante extrae credenciales almacenadas en caché. Si encuentra credenciales de administradores que hayan iniciado sesión previamente, puede pivotar hacia la red de servidores.

En esta red se encuentran activos críticos y cuentas con mayores privilegios.

### Compromiso del dominio

Mediante la extracción progresiva de credenciales en servidores, el atacante puede alcanzar cuentas con privilegios de Domain Admin.

Con este acceso llega al Domain Controller, el activo más crítico del entorno.

### Persistencia y explotación masiva

Una vez comprometido el controlador de dominio:

- Se vuelcan credenciales de todos los usuarios.
- Se crackean contraseñas débiles.
- Se obtiene la cuenta asociada al TGT de Kerberos.
- Se genera un Golden Ticket con persistencia prolongada.

Para invalidar un Golden Ticket es necesario restablecer la contraseña de Kerberos en dos ocasiones consecutivas.

### Exfiltración e impacto

El atacante puede descifrar secretos almacenados en navegadores y acceder a cuentas corporativas. Esto permite:

- Exfiltrar información confidencial.
- Robar documentación técnica.
- Realizar extorsión bajo amenaza de publicación.

El objetivo final suele ser económico o estratégico.

## Recomendaciones fundamentales de seguridad

### Segmentación de comunicaciones

Limitar la comunicación entre estaciones de trabajo y entre clientes y servidores.

### Filtrado de salida

Restringir conexiones salientes desde servidores para evitar exfiltración y autenticaciones externas maliciosas.

### Evitar almacenamiento de credenciales

Impedir el cacheo de credenciales en equipos de usuario.

### Gestión periódica de Kerberos

Restablecer periódicamente la cuenta TGT y realizar doble cambio para invalidar posibles tickets fraudulentos.

### Control de acceso a documentos sensibles

Aplicar políticas que eviten lectura no autorizada incluso en caso de publicación accidental.

### Reducción de superficie de ataque

Limitar servicios, protocolos y puertos abiertos.

### Auditoría continua

Revisar cuentas, grupos y privilegios de forma periódica.

### Control de aplicaciones

Implementar mecanismos que restrinjan la ejecución de software no autorizado.

### Sistemas trampa

Desplegar honeypots o honey tokens para detectar actividad maliciosa temprana.

### Protección de sesiones

Evitar la enumeración remota de sesiones activas.

### Protección de procesos críticos

Asegurar procesos donde se almacenan credenciales de dominio.

### Deshabilitar administradores locales

Evitar el uso de cuentas administrativas locales en estaciones de trabajo y servidores.

## Conclusión

El compromiso total de un dominio suele ser consecuencia de múltiples fallos encadenados.

La combinación de segmentación, control de privilegios, auditoría continua, cifrado y monitorización reduce significativamente la probabilidad de que un atacante complete toda la Kill Chain.