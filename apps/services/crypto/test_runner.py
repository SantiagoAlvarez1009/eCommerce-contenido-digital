import io
import shutil
import tempfile
from pathlib                import Path

from django.core.management import call_command
from django.test.runner     import DiscoverRunner
from django.test.utils      import override_settings


class SigningKeysTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._keys_dir = Path(tempfile.mkdtemp())
        self._keys_override = override_settings(
            SIGNING_PRIVATE_KEY_PATH = self._keys_dir / 'signing_key.pem',
            SIGNING_PUBLIC_KEY_PATH  = self._keys_dir / 'signing_key.pub.pem',
        )
        self._keys_override.enable()
        call_command('generate_signing_keys', stdout=io.StringIO())

    def teardown_test_environment(self, **kwargs):
        self._keys_override.disable()
        shutil.rmtree(self._keys_dir, ignore_errors=True)
        super().teardown_test_environment(**kwargs)