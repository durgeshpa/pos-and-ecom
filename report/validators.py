# -*- coding: utf-8 -*-

def validate_input_params(input_params, required_params):
    errors = []
    required_keys = required_params.keys()
    for key in required_keys:
        if not input_params.get(key):
            errors.append(str(key) + " is mandatory for report generation")
    return errors
    