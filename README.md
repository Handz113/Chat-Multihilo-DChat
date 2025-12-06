# Chat-Multihilo-DChat
Chat multihilo encargado de establecer comunicación en entornos de trabajo y/o empresariales con el objetivo de tener una comunicación local sin la necesidad de recurrir a terceros. Agente IA implementado para resumir conversaciones (dedicado a conversaciones con orientación a entornos empresariales)

-- Manual install --

1.Descargue los archivos y guardelos en una carpeta, a excepción de Host 0.0.3.py y las server keys así como el certificado.

2.En su servidor guarde el archivo Host 0.0.3.py con el certificado y llave del servidor y ejecute el codigo en su terminal de preferencia

-- Server Key and Certificate --


Para la ejecución, el servidor requiere los archivos server.crt y server.key en la raíz del proyecto. El archivo server.key no se subió a GitHub por razones de seguridad. Debes generar tu propia llave o, si ya tienes el archivo de un entorno de prueba, usarlo.

-- Routing --


Para tener un direccionamiento correcto, en 'Host 0.0.3.py' y en 'network_manager.py' se debe cambiar la dirección IPv4 a la dirección deseada, siendo el archivo Host el servidor y el network_manager el cliente, ambos deben tener la misma dirección IPv4.


-- IA --

Mantener el servicio Ollama activo antes de iniciar el servidor
