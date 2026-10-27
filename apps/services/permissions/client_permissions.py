from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


class ClientPermissions:
    @staticmethod
    def create_client_permissions():
        """
        Create permissions for the client role.
        """
        # Get the content type for the User model
        user_content_type = ContentType.objects.get(app_label='users', model='user')

        # Create permissions for the client role
        Permission.objects.get_or_create(
            codename='modify_its_profile',
            name='Can modify its profile',
            content_type=user_content_type
        )
        Permission.objects.get_or_create(
            codename='consult_products',
            name='Can consult products',
            content_type=user_content_type
        )
        Permission.objects.get_or_create(
            codename='add_products_to_cart',
            name='Can add products to cart',
            content_type=user_content_type
        )
        Permission.objects.get_or_create(
            codename='create_orders',
            name='Can create orders',
            content_type=user_content_type
        )
        Permission.objects.get_or_create(
            codename='make_payments',
            name='Can make payments',
            content_type=user_content_type
        )
        Permission.objects.get_or_create(
            codename='consult_its_orders',
            name='Can consult its orders',
            content_type=user_content_type
        )
        Permission.objects.get_or_create(
            codename='download_purchased_products',
            name='Can download purchased products',
            content_type=user_content_type
        )
        Permission.objects.get_or_create(
            codename='consult_its_recipts',
            name='Can consult its receipts',
            content_type=user_content_type
        )
        Permission.objects.get_or_create(
            codename='verify_digital_recipt_fingerprint',
            name='Can verify digital receipt fingerprint',
            content_type=user_content_type
        )
