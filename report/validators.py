# -*- coding: utf-8 -*-

from distutils.log import error
from ftplib import error_reply


def validate_input_params(input_params, required_params):
    errors = []
    required_keys = required_params.keys()
    for key in required_keys:
        if not input_params.get(key):
            errors.append(str(key) + " is mandatory for report generation")
    return errors
    