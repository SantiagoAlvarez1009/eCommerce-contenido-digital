#!/bin/bash
# Script de instrucciones para crear la CA y certificados TLS
# Entregablede Adan Fraire

echo "Creando directorio para los certificados..."
mkdir -p certificados_tls
cd certificados_tls

echo "1. Generando llave privada de la Autoridad Certificadora (CA)..."
openssl genrsa -out ca.key 4096

echo "2. Generando certificado raiz de la CA local..."
openssl req -x509 -new -nodes -key ca.key -sha256 -days 1024 -out ca.crt -subj "/C=MX/ST=Chihuahua/L=Ciudad Juarez/O=Proyecto Universitario/CN=CA Local Adan"

echo "3. Generando llave privada del servidor web..."
openssl genrsa -out server.key 2048

echo "4. Creando Solicitud de Firma de Certificado (CSR) para localhost..."
openssl req -new -key server.key -out server.csr -subj "/C=MX/ST=Chihuahua/L=Ciudad Juarez/O=Proyecto Universitario/CN=localhost"

echo "5. Firmando el certificado del servidor usando la CA local..."
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 500 -sha256

echo "Proceso completado. Los archivos ca.crt, server.key y server.crt se encuentran en la carpeta certificados_tls/."