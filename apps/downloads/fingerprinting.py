"""
Insertion and recovery of the fingerprint inside the distributed content.
Soporta imágenes (LSB) y archivos de texto plano (Zero-Width Characters).
"""
from io import BytesIO
from PIL import Image
from stegano import lsb

# Constantes para caracteres invisibles (Zero-Width) en archivos de texto
ZW_SEP = '\u200D'  # Separador invisible
ZW_0 = '\u200B'    # Representa un '0' en binario
ZW_1 = '\u200C'    # Representa un '1' en binario

def embed(data, fingerprint):
    """Oculta el fingerprint dependiendo del tipo de archivo."""
    
    # 1. Intentar inyectar como IMAGEN (Técnica LSB)
    try:
        image = Image.open(BytesIO(data))
        secret_image = lsb.hide(image, fingerprint)
        output = BytesIO()
        secret_image.save(output, format="PNG")
        return output.getvalue()
    except Exception:
        pass # Si falla, asumimos que no es una imagen y pasamos al texto

    # 2. Intentar inyectar como TEXTO (Técnica de Caracteres Invisibles)
    try:
        text = data.decode('utf-8')
        # Convertimos el texto del fingerprint a código binario (0s y 1s)
        bin_str = ''.join(format(ord(c), '08b') for c in fingerprint)
        # Transformamos los 0s y 1s en caracteres que no se ven en la pantalla
        invisible_str = ZW_SEP + ''.join(ZW_1 if b == '1' else ZW_0 for b in bin_str)
        # Pegamos los caracteres invisibles al final del documento
        return (text + invisible_str).encode('utf-8')
    except Exception:
        pass # Si tampoco es texto válido, lo devolvemos original para no romperlo
        
    return data

def extract(data):
    """Recupera el fingerprint oculto de un archivo."""
    
    # 1. Intentar extraer de IMAGEN
    try:
        image = Image.open(BytesIO(data))
        fingerprint = lsb.reveal(image)
        if fingerprint:
            return fingerprint
    except Exception:
        pass

    # 2. Intentar extraer de TEXTO
    try:
        text = data.decode('utf-8')
        # Buscamos si existe nuestro separador invisible
        if ZW_SEP in text:
            invisible_str = text.split(ZW_SEP)[-1]
            # Convertimos los caracteres invisibles de vuelta a binario
            bin_str = ''.join('1' if c == ZW_1 else '0' for c in invisible_str if c in (ZW_0, ZW_1))
            if bin_str:
                # Convertimos el binario de vuelta al texto original (el ID del fingerprint)
                chars = [chr(int(bin_str[i:i+8], 2)) for i in range(0, len(bin_str), 8)]
                return ''.join(chars)
    except Exception:
        pass

    return None