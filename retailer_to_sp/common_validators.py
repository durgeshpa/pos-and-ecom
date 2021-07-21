from pos.models import PaymentType

def validate_payment_type(id):
    """
        Validate Payment Type
    """
    try:
        payment_type = PaymentType.objects.get(id=id)
    except:
        return {'error': 'Provide valid payment type'}
    return {'data': payment_type}