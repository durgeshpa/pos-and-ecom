from django.db.models import CharField


class CaseInsensitiveFieldMixin:
    """[summary]
    Mixin to make django fields case insensitive
    """

    def get_prep_value(self, value):

        return str(value).title()

    def to_python(self, value):

        value = super().to_python(value)

        # Value can be None so check that it's a string before lowercasing.
        if isinstance(value, str):

            return value.title()

        return value


class CaseInsensitiveCharField(CaseInsensitiveFieldMixin, CharField):
    """[summary]
    Makes django CharField case insensitive \n
    Extends both the `CaseInsensitiveMixin` and  CharField \n
    Then you can import
    """

    def __init__(self, *args, **kwargs):

        super(CaseInsensitiveCharField, self).__init__(*args, **kwargs)