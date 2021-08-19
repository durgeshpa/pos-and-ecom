

def validate_ledger_request(request):
    sku = request.GET.get('sku')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if not sku:
        return {"error": "please select sku"}

    if not start_date:
        return {"error": "please select start_date"}

    if not end_date:
        return {"error": "please select end_date"}
    return {"data": {"sku": sku, "start_date": start_date, "end_date": end_date}}
