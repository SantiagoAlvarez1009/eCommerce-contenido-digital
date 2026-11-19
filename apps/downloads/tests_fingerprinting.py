"""
Tests for the fingerprinting module (downloads/fingerprinting.py) with the three
supported formats, focused on PDF, plus the download flow for a PDF product.
"""
import io

from django.urls import reverse
from pypdf       import PdfReader, PdfWriter

from apps.security_events.models import SecurityEvent
from apps.services.testing       import AppTestCase, pdf_bytes, png_bytes
from . import fingerprinting
from .models   import Download, FingerPrint
from .services import identify_content, new_fingerprint_value


def pdf_text(data):
    return ''.join(page.extract_text() or '' for page in PdfReader(io.BytesIO(data)).pages)


class FingerprintFormatTests(AppTestCase):

    def setUp(self):
        self.fp = new_fingerprint_value()

    def test_format_is_detected_by_content(self):
        self.assertEqual(fingerprinting.detect_format(pdf_bytes()), 'pdf')
        self.assertEqual(fingerprinting.detect_format(png_bytes()), 'png')
        self.assertEqual(fingerprinting.detect_format('texto con acentos: ñ'.encode('utf-8')), 'txt')
        self.assertIsNone(fingerprinting.detect_format(b'\xff\xfe\x00\x01binario'))

    def test_each_format_recovers_its_fingerprint(self):
        for name, data in (('txt', b'Texto de prueba'), ('pdf', pdf_bytes()), ('png', png_bytes())):
            with self.subTest(format=name):
                marked = fingerprinting.embed(data, self.fp)
                self.assertNotEqual(marked, data)
                self.assertEqual(fingerprinting.extract(marked), self.fp)

    def test_unmarked_files_have_no_fingerprint(self):
        for data in (b'Texto de prueba', pdf_bytes(), png_bytes()):
            self.assertIsNone(fingerprinting.extract(data))

    def test_unsupported_format_raises_instead_of_returning_unmarked_copy(self):
        with self.assertRaises(fingerprinting.FingerprintError):
            fingerprinting.embed(b'\xff\xfe\x00\x01binario', self.fp)

    def test_corrupt_pdf_raises(self):
        with self.assertRaises(fingerprinting.FingerprintError):
            fingerprinting.embed(b'%PDF-1.4 basura', self.fp)

    def test_png_in_palette_mode_is_marked(self):
        marked = fingerprinting.embed(png_bytes(mode='P'), self.fp)
        self.assertEqual(fingerprinting.extract(marked), self.fp)


class PdfFingerprintTests(AppTestCase):

    def setUp(self):
        self.fp       = new_fingerprint_value()
        self.original = pdf_bytes(pages=3)
        self.marked   = fingerprinting.embed(self.original, self.fp)

    def test_marked_pdf_is_still_a_valid_pdf_with_same_pages(self):
        reader = PdfReader(io.BytesIO(self.marked))
        self.assertEqual(len(reader.pages), 3)

    def test_fingerprint_is_in_metadata(self):
        reader = PdfReader(io.BytesIO(self.marked))
        self.assertEqual(reader.metadata[fingerprinting.PDF_METADATA_KEY], self.fp)

    def test_visible_text_is_preserved(self):
        self.assertIn('Contenido original del manual - pagina 1', pdf_text(self.marked))

    def test_fingerprint_text_is_invisible(self):
        # Render mode 3: neither filled nor stroked. The text is extractable but not drawn.
        reader   = PdfReader(io.BytesIO(self.marked))
        contents = reader.pages[0].get_contents().get_data()
        self.assertIn(b'3 Tr', contents)
        self.assertIn(self.fp.encode(), contents)

    def test_fingerprint_survives_metadata_removal(self):
        # Copying only the pages to a new PDF drops the metadata.
        writer = PdfWriter()
        for page in PdfReader(io.BytesIO(self.marked)).pages:
            writer.add_page(page)
        output = io.BytesIO()
        writer.write(output)
        stripped = output.getvalue()

        self.assertIsNone((PdfReader(io.BytesIO(stripped)).metadata or {}).get(fingerprinting.PDF_METADATA_KEY))
        self.assertEqual(fingerprinting.extract(stripped), self.fp)

    def test_fingerprint_survives_extracting_a_single_page(self):
        writer = PdfWriter()
        writer.add_page(PdfReader(io.BytesIO(self.marked)).pages[2])
        output = io.BytesIO()
        writer.write(output)
        self.assertEqual(fingerprinting.extract(output.getvalue()), self.fp)


class PdfDownloadTests(AppTestCase):

    def setUp(self):
        self.original = pdf_bytes(pages=2)
        self.product  = self.make_product('Manual PDF', content=self.original, file_name='manual.pdf')
        self.user     = self.make_user()
        self.client.force_login(self.user)

    def download(self):
        response = self.client.get(reverse('downloads:download', args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)
        return response, b''.join(response.streaming_content)

    def test_downloaded_pdf_identifies_user_and_order(self):
        order = self.buy(self.product)
        response, content = self.download()

        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(content.startswith(b'%PDF-'))
        record = identify_content(content)
        self.assertIsNotNone(record)
        self.assertEqual(record.user, self.user)
        self.assertEqual(record.order, order)
        self.assertEqual(record.product, self.product)

    def test_original_pdf_is_not_modified(self):
        self.buy(self.product)
        self.download()
        self.assertTrue(self.product.file_is_intact())

    def test_each_buyer_gets_a_different_pdf_fingerprint(self):
        self.buy(self.product)
        _, first = self.download()

        other = self.make_user('otro@test.com')
        self.client.force_login(other)
        self.buy(self.product)
        _, second = self.download()

        self.assertNotEqual(fingerprinting.extract(first), fingerprinting.extract(second))
        self.assertEqual(identify_content(second).user, other)


class UnmarkableFileTests(AppTestCase):
    """If a stored product cannot be marked, no unmarked copy is delivered."""

    def setUp(self):
        # Bypasses ProductForm on purpose (e.g. a file placed directly in storage).
        self.product = self.make_product('Binario', content=b'\xff\xfe\x00\x01binario', file_name='binario.bin')
        self.client.force_login(self.make_user())
        self.buy(self.product)

    def test_download_is_refused_and_logged_as_failure(self):
        response = self.client.get(reverse('downloads:download', args=[self.product.pk]))
        self.assertRedirects(response, reverse('downloads:library'))
        event = SecurityEvent.objects.filter(event=SecurityEvent.Event.DOWNLOAD).latest('created_at')
        self.assertEqual(event.result, SecurityEvent.Result.FAILURE)

    def test_no_fingerprint_or_download_record_is_kept(self):
        self.client.get(reverse('downloads:download', args=[self.product.pk]))
        self.assertFalse(FingerPrint.objects.exists())
        self.assertFalse(Download.objects.exists())
        self.assertFalse(SecurityEvent.objects.filter(event=SecurityEvent.Event.FINGERPRINT_CREATED).exists())