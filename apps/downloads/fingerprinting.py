from io import BytesIO
from PIL import Image
from stegano import lsb
import json

def embed(data, fingerprint):
    """
    Recibe los bytrs de la imagen originales yel identificador
    Retorna los bytes de la nueva imagen con el identificador oculto esteganograficamente
    """
    try:
        image = Image.open(BytesIO(data))

        secret_image = lsb.hide(image, fingerprint)

        output = BytesIO()

        secret_image.save(output, format="PNG")

        return output.getvalue()
    except Exception as e:
        print(f"Error al aplicar esteganografia: {e}")
        return data

def extract(data):
    """
    Recibe los bytes de un archivo sospechoso
    y retorna el fingeeprint extraido, o Nonesi no se encontro nada
    """
    try:
        image = Image.open(BytesIO(data))
        fingerprint = lsb.reveal(image)

        if fingerprint:
            return fingerprint
        return None
    except Exception:
        return None 
