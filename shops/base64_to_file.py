import base64
import io
import uuid
import sys
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import SuspiciousOperation


# WARNING: quick and dirty, should be used for reference only.

def to_file(file_from_POST):
    """base64 encoded file to Django InMemoryUploadedFile that can be placed into request.FILES."""
    # 'data:image/png;base64,<base64 encoded string>'
    try:
        idx = file_from_POST[:50].find(',')  # comma should be pretty early on

        if not idx or not file_from_POST.startswith('data:image/'):
            raise Exception()

        base64file = file_from_POST[idx+1:]
        attributes = file_from_POST[:idx]
        content_type = attributes[len('data:'):attributes.find(';')]
    except Exception as e:
        raise SuspiciousOperation("Invalid Image document")

    f = io.BytesIO(base64.b64decode(base64file))
    image = InMemoryUploadedFile(f,
                                 field_name=None,
                                 name=uuid.uuid4().hex + '.jpg',  # use UUIDv4 or something
                                 content_type=content_type,
                                 size=sys.getsizeof(f),
                                 charset=None)
    return image
