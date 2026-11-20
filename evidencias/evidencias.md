# Evidencias de pruebas

Evidencias de las pruebas mínimas obligatorias y resumen de las pruebas generales de la aplicación.

| | |
|---|---|
| **Suite** | `python manage.py test apps -v 2` |
| **Resultado** | 218 tests, todos aprobados, ver [`resultado_tests.txt`](resultado_tests.txt) |
| **Entorno** | Python 3.13, Django 6.1, SQLite en memoria para los tests |

## Pruebas mínimas obligatorias

| # | Prueba | Resultado esperado | Cómo se verifica | Resultado | Evidencia |
|---|---|---|---|---|---|
| 1 | Contraseña incorrecta | Acceso rechazado | `users/tests.py` → `LoginTests.test_wrong_password_is_rejected` | Aprobada | [`resultado_tests.txt`](resultado_tests.txt) |
| 2 | CLIENTE intenta una función administrativa | Acceso rechazado | `users/tests.py` → `RoleAccessTests.test_client_cannot_use_admin_functions` (lista de usuarios, cambio de rol, desactivar cuenta y revocar sesiones: 403 y el usuario objetivo no cambia) | Aprobada | [`resultado_tests.txt`](resultado_tests.txt)|
| 3 | OPERADOR intenta cambiar roles | Acceso rechazado | `users/tests.py` → `RoleAccessTests.test_operator_cannot_change_roles`, `test_operator_cannot_promote_itself` | Aprobada | [`resultado_tests.txt`](resultado_tests.txt) |
| 4 | ADMINISTRADOR autorizado | Operación permitida | `users/tests.py` → `RoleAccessTests.test_admin_can_change_roles` | Aprobada | [`resultado_tests.txt`](resultado_tests.txt) |
| 5 | Certificado TLS correcto | Conexión aceptada | `curl --cacert ca.crt` → HTTP 200, exit 0; `openssl s_client -CAfile ca.crt` → `Verify return code: 0 (ok)` | Aprobada | Captura `05_TLS-Correcto.png` |
| 6 | Certificado no confiable | Conexión rechazada | `curl` sin la CA del proyecto → exit 60 (certificado no confiable); `openssl s_client` sin la CA → `Verify return code: 20/21`  | Aprobada | Captura `06_TLS-NoConfiable.png` |
| 7 | Comprobante original | Firma digital válida | `payments/tests.py` → `ReceiptVerificationFlowTests.test_downloaded_original_receipt_is_valid`; `payments/tests_receipts.py` → `test_verify_page_accepts_original_receipt` | Aprobada | [`comprobantes/verificacion.txt`](comprobantes/verificacion.txt) |
| 8 | Comprobante modificado | Firma digital inválida | `payments/tests.py` → `ReceiptVerificationFlowTests.test_downloaded_receipt_modified_is_invalid` (total cambiado, un byte, línea agregada); `payments/tests_receipts.py` → `test_verify_page_rejects_modified_receipt` | Aprobada | [`comprobantes/verificacion.txt`](comprobantes/verificacion.txt) |
| 9 | Producto descargado | Fingerprint recuperable | `downloads/tests.py` → `test_text_fingerprint_is_recoverable` (.txt), `test_image_fingerprint_is_recoverable` (.png); `downloads/tests_fingerprinting.py` → `PdfDownloadTests.test_downloaded_pdf_identifies_user_and_order` (.pdf) | Aprobada | [`fingerprint/identify_copy.txt`](fingerprint/identify_copy.txt) |
| 10 | CLIENTE intenta descargar producto no comprado | Acceso rechazado | `downloads/tests.py` → `test_client_cannot_download_product_not_purchased`, `test_client_cannot_download_with_failed_payment`, `test_client_cannot_download_product_bought_by_other_user` | Aprobada | [`resultado_tests.txt`](resultado_tests.txt) |
| 11 | Archivo original | Hash esperado | `products/tests.py` → `ProductIntegrityTests.test_original_file_has_expected_hash`; `downloads/tests_integrity.py` → `test_original_file_matches_expected_hash` | Aprobada | [`integridad/verify_intacto.txt`](integridad/verify_intacto.txt) |
| 12 | Archivo modificado | Hash diferente | `products/tests.py` → `ProductIntegrityTests.test_modified_file_has_different_hash`; `downloads/tests_integrity.py` → `test_modified_file_has_different_hash`, `test_tampered_product_cannot_be_downloaded` | Aprobada | [`integridad/verify_alterado.txt`](integridad/verify_alterado.txt) |
| 13 | Restauración de respaldo | Información crítica recuperada | Respaldos gestionados en AWS: restauración de un respaldo y comprobación de que los datos críticos (usuarios, órdenes, productos) se recuperan |  Aprobada | Captura `13_Respaldo.png` |

Las pruebas 5, 6 y 13 dependen de la infraestructura (servidor, certificados y respaldos) y se documentan con el despliegue, no con la suite de Django.

## Pruebas generales por módulo

| Módulo | Archivos | Tests | Qué cubre |
|---|---|---|---|
| users | `tests.py` | 38 | Almacenamiento con Argon2id (sal aleatoria, sin columna de contraseña en claro, migración desde PBKDF2), registro, login y logout, perfil, recuperación de contraseña con token de un solo uso, acceso por rol y administración de cuentas y sesiones |
| products | `tests.py` | 24 | Hash SHA-256 de los archivos, acceso solo para OPERADOR, alta, edición y activación de productos, validación de archivos (.txt, .pdf, .png; el contenido debe coincidir con la extensión; se rechazan archivos dañados, cifrados o de más de 10 MB) |
| catalog | `tests.py` | 17 | Catálogo público con solo productos disponibles, búsqueda, paginación, entradas maliciosas en la búsqueda, detalle sin exponer la ubicación del archivo y botones según el usuario |
| cart | `tests.py` | 15 | Agregar, quitar y vaciar productos, total, carrito aislado por usuario, productos ocultos o ya comprados y redirecciones solo dentro del sitio |
| orders | `tests.py`, `tests_status.py`, `tests_seed.py` | 29 | Checkout, precio congelado en la orden, órdenes visibles solo para su dueño, gestión por OPERADOR, transiciones de estado válidas y datos de prueba |
| payments | `tests.py`, `tests_receipts.py`, `tests_signing.py` | 40 | Pago simulado sin datos bancarios, pago aprobado o rechazado, reintento, órdenes pagadas o canceladas, contenido del comprobante, acceso solo del dueño, firma Ed25519 y verificación con los archivos descargados, clave privada cifrada |
| downloads | `tests.py`, `tests_fingerprinting.py`, `tests_integrity.py` | 36 | Descarga solo de productos comprados, fingerprint en .txt, .png y .pdf (invisible, distinto por comprador, sobrevive al borrado de metadatos y a la extracción de páginas), archivos que no se pueden marcar, integridad antes de entregar y comandos `identify_copy` y `verify_product_hashes` |
| security_events | `tests.py`, `tests_origin.py` | 19 | Registro de cada evento (login, logout, recuperación, orden, pago, firma, descarga, fingerprint, rol, cuenta, sesiones), sin contraseñas en el log, origen (IP), eventos no modificables y lista solo para ADMINISTRADOR |
| **Total** | | **218** | |

## Contenido de la carpeta

| Ruta | Contenido |
|---|---|
| `resultado_tests.txt` | Salida completa de la suite con el resultado de cada test |
| `integridad/verify_intacto.txt` | `verify_product_hashes` con todos los productos intactos |
| `integridad/verify_alterado.txt` | `verify_product_hashes` después de modificar un producto en el almacenamiento: detecta el hash distinto |
| `fingerprint/*_original.*` | Productos originales (.txt y .pdf) |
| `fingerprint/*_copia*` | Copias descargadas por dos clientes distintos; se ven idénticas al original |
| `fingerprint/identify_copy.txt` | `identify_copy` sobre cada archivo: el original no tiene fingerprint y cada copia identifica a su comprador y su orden |
| `comprobantes/comprobante_orden_*.txt` / `.sig` | Comprobante descargado y su firma |
| `comprobantes/comprobante_orden_*_modificado.txt` | El mismo comprobante con el total alterado |
| `comprobantes/clave_publica_comprobantes.pem` | Clave pública para verificar la firma (clave temporal de esta evidencia; la privada no se publica) |
| `comprobantes/verificacion.txt` | Resultado de verificar el original (válida) y el modificado (inválida) |
| `capturas/` | Capturas de pantalla de evidencias no cubiertas en tests automáticos |

Las evidencias de integridad, fingerprint y comprobantes se generan con la aplicación real (vistas, servicios y comandos), sobre una base de datos, una carpeta de media y unas claves de firma temporales que se borran al terminar.
