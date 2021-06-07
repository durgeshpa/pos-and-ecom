from django.http import QueryDict
import json
from rest_framework import parsers


class MultipartJsonParser(parsers.MultiPartParser):
    """
      Parser for multipart form data which might contain JSON values
      in some fields as well as file data.
    """
    def parse(self, stream, media_type=None, parser_context=None):
        """
            Parses the incoming bytestream as a multipart encoded form,
            and returns a DataAndFiles object.
            data will be a QueryDict containing all the form parameters, and JSON decoded where available.
            files will be a QueryDict containing all the form files.
        """
        result = super().parse(
            stream,
            media_type=media_type,
            parser_context=parser_context
        )
        # find the data field and parse it
        data = json.loads(result.data["data"])
        qdict = QueryDict('', mutable=True)
        qdict.update(data)
        return parsers.DataAndFiles(qdict, result.files)