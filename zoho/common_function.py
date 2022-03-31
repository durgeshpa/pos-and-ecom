import csv
from datetime import datetime
from django.http import HttpResponse

from zoho.models import ZohoInvoice, ZohoInvoiceItem


class ZohoInvoiceCls:
    @classmethod
    def create_zoho_invoice(cls, validated_rows, created_by):
        try:
            for row in validated_rows:
                zoho_invoice_obj, created = ZohoInvoice.objects.update_or_create(
                    invoice_id=row['invoice_id'],
                    defaults={'invoice_date': row['invoice_date'], 'invoice_number': row['invoice_number'],
                              'invoice_status': row['invoice_status'],
                              'due_date': row['due_date'], 'purchaseorder': row['purchaseorder'],
                              'expected_payment_date': row['expected_payment_date'],
                              'last_payment_date': row['last_payment_date'],
                              'payment_terms': row['payment_terms'],
                              'payment_terms_label': row['payment_terms_label'],
                              'sales_order_number': row['sales_order_number'],
                              'expense_reference_id': row['expense_reference_id'],
                              'recurrence_name': row['recurrence_name'],
                              'paypal': row['paypal'],
                              'authorize_net': row['authorize_net'],
                              'google_checkout': row['google_checkout'],
                              'payflow_pro': row['payflow_pro'],
                              'stripe': row['stripe'],
                              'paytm': row['paytm'],
                              'checkout': row['checkout'],
                              'braintree': row['braintree'],
                              'forte': row['forte'],
                              'worldpay': row['worldpay'],
                              'payments_pro': row['payments_pro'],
                              'square': row['square'],
                              'wepay': row['wepay'],
                              'razorpay': row['razorpay'],
                              'gocardless': row['gocardless'],
                              'partial_payments': row['partial_payments'],
                              'billing_street2': row['billing_street2'],
                              'shipping_street2': row['shipping_street2'],
                              'shipping_phone_number': row['shipping_phone_number'],
                              'primary_contact_emailid': row['primary_contact_emailid'],
                              'primary_contact_mobile': row['primary_contact_mobile'],
                              'primary_contact_phone': row['primary_contact_phone'],
                              'estimate_number': row['estimate_number'],
                              'custom_charges': row['custom_charges'],
                              'shipping_bill': row['shipping_bill'],
                              'shipping_bill_date': row['shipping_bill_date'],
                              'shipping_bill_total': row['shipping_bill_total'],
                              'portcode': row['portcode'],
                              'reference_invoice': row['reference_invoice'],
                              'reference_invoice_date': row['reference_invoice_date'],
                              'gst_registration_number_reference_invoice':
                                  row['gst_registration_number_reference_invoice'],
                              'reason_for_issuing_debit_note': row['reason_for_issuing_debit_note'],
                              'e_commerce_operator_name': row['e_commerce_operator_name'],
                              'e_commerce_operator_gstin': row['e_commerce_operator_gstin'],
                              'customer_id': row['customer_id'],
                              'customer_name': row['customer_name'],
                              'place_of_supply': row['place_of_supply'],
                              'place_of_supply_with_state_code': row[
                                  'place_of_supply_with_state_code'],
                              'gst_treatment': row['gst_treatment'],
                              'is_inclusive_tax': row['is_inclusive_tax'],
                              'currency_code': row['currency_code'],
                              'exchange_rate': row['exchange_rate'],
                              'discount_type': row['discount_type'],
                              'is_discount_before_tax': row['is_discount_before_tax'],
                              'template_name': row['template_name'],
                              'entity_discount_percent': row['entity_discount_percent'],
                              'tcs_tax_name': row['tcs_tax_name'],
                              'tcs_percentage': row['tcs_percentage'],
                              'subtotal': row['subtotal'],
                              'total': row['total'],
                              'balance': row['balance'],
                              'adjustment': row['adjustment'],
                              'adjustment_description': row['adjustment_description'],
                              'notes': row['notes'],
                              'terms_conditions': row['terms_conditions'],
                              'e_invoice_status': row['e_invoice_status'],
                              'e_invoice_reference_number': row['e_invoice_reference_number'],
                              'tcs_amount': row['tcs_amount'],
                              'entity_discount_amount': row['entity_discount_amount'],
                              'branch_id': row['branch_id'],
                              'branch_name': row['branch_name'],
                              'shipping_charge': row['shipping_charge'],
                              'shipping_charge_tax_id': row['shipping_charge_tax_id'],
                              'shipping_charge_tax_amount': row['shipping_charge_tax_amount'],
                              'shipping_charge_tax_name': row['shipping_charge_tax_name'],
                              'shipping_charge_tax_percentage': row[
                                  'shipping_charge_tax_percentage'],
                              'shipping_charge_tax_type': row['shipping_charge_tax_type'],
                              'shipping_charge_tax_exemption_code': row[
                                  'shipping_charge_tax_exemption_code'],
                              'shipping_charge_sac_code': row['shipping_charge_sac_code'],
                              'billing_attention': row['billing_attention'],
                              'billing_address': row['billing_address'],
                              'billing_city': row['billing_city'],
                              'billing_state': row['billing_state'],
                              'billing_country': row['billing_country'],
                              'billing_code': row['billing_code'],
                              'billing_phone': row['billing_phone'],
                              'billing_fax': row['billing_fax'],
                              'shipping_attention': row['shipping_attention'],
                              'shipping_address': row['shipping_address'],
                              'shipping_city': row['shipping_city'],
                              'shipping_state': row['shipping_state'],
                              'shipping_country': row['shipping_country'],
                              'shipping_code': row['shipping_code'],
                              'shipping_fax': row['shipping_fax'],
                              'e_invoice_qrjson': row['e_invoice_qrjson'],
                              'e_invoice_qr_raw_data': row['e_invoice_qr_raw_data'],
                              'e_invoice_ack_number': row['e_invoice_ack_number'],
                              'e_invoice_ack_date': row['e_invoice_ack_date'],
                              'e_invoice_cancel_remark': row['e_invoice_cancel_remark'],
                              'e_invoice_cancel_reason': row['e_invoice_cancel_reason'],
                              'e_invoice_failure_reason': row['e_invoice_failure_reason'],
                              'supplier_org_name': row['supplier_org_name'],
                              'supplier_gst_registration_number': row[
                                  'supplier_gst_registration_number'],
                              'supplier_street_address': row['supplier_street_address'],
                              'supplier_city': row['supplier_city'],
                              'supplier_state': row['supplier_state'],
                              'supplier_country': row['supplier_country'],
                              'supplier_zipcode': row['supplier_zipcode'],
                              'supplier_phone': row['supplier_phone'],
                              'supplier_e_mail': row['supplier_e_mail'],
                              'cgst_rate_percentage': row['cgst_rate_percentage'],
                              'sgst_rate_percentage': row['sgst_rate_percentage'],
                              'igst_rate_percentage': row['igst_rate_percentage'],
                              'cess_rate_percentage': row['cess_rate_percentage'],
                              'cgst_fcy': row['cgst_fcy'],
                              'sgst_fcy': row['sgst_fcy'],
                              'igst_fcy': row['igst_fcy'],
                              'cess_fcy': row['cess_fcy'],
                              'cgst': row['cgst'],
                              'sgst': row['sgst'],
                              'igst': row['igst'],
                              'cess': row['cess'],
                              'reverse_charge_tax_name': row['reverse_charge_tax_name'],
                              'reverse_charge_tax_rate': row['reverse_charge_tax_rate'],
                              'reverse_charge_tax_type': row['reverse_charge_tax_type'],
                              'gst_identification_number_gstin': row[
                                  'gst_identification_number_gstin'],
                              'nature_of_collection': row['nature_of_collection'],
                              'project_id': row['project_id'],
                              'project_name': row['project_name'],
                              'hsn_sac': row['hsn_sac'],
                              'round_off': row['round_off'],
                              'sales_person': row['sales_person'],
                              'subject': row['subject'],
                              'reference_invoice_type': row['reference_invoice_type'],
                              'account': row['account'],
                              'account_code': row['account_code'],
                              'supply_type': row['supply_type']
                              },
                )

                ZohoInvoiceItem.objects.update_or_create(
                    product_id=row['product_id'], zoho_invoice=zoho_invoice_obj,
                    defaults={
                        'item_name': row['item_name'], 'item_desc': row['item_desc'], 'quantity': row['quantity'],
                        'discount': row['discount'], 'discount_amount': row['discount_amount'],
                        'item_total': row['item_total'], 'tax_id': row['tax_id'], 'item_tax_amount':
                            row['item_tax_amount'], 'usage_unit': row['usage_unit'], 'item_price': row['item_price'],
                        'item_type': row['item_type'], 'item_tax': row['item_tax'], 'item_tax_percentage':
                            row['item_tax_percentage'], 'item_tax_type': row['item_tax_type'],
                        'item_tax_exemption_reason': row['item_tax_exemption_reason']
                    }
                )

        except Exception as e:
            print(e)


def error_invoice_credit_note_csv_file(data_list, file_name):
    # Write error msg in csv sheet.
    filename = file_name.csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachement; filename="{}"'.format(filename)

    writer = csv.writer(response)
    for row in data_list:
        writer.writerow(row)

    return response

