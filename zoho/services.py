import csv
import codecs
from .models import ZohoCustomers
from django.http import HttpResponse


def zoho_credit_note_data_upload(credit_note_file):
    pass


def zoho_invoice_data_upload(invoice_file):
    reader = csv.reader(codecs.iterdecode(invoice_file, 'utf-8'))
    next(reader)
    for row in reader:
        pass


def zoho_customers_file_upload(request, customer_file):
    reader = csv.DictReader(codecs.iterdecode(customer_file, 'utf-8'))
    error = []
    row_no = 1
    count = 0
    filename = "zoho_customers_file_upload.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(
        ['Created Time', 'Last Modified Time', 'Display Name', 'Company Name', 'Salutation',
         'First Name', 'Last Name', 'Phone', 'Currency Code', 'Notes',
         'Website', 'Status', 'Opening Balance', 'Exchange Rate', 'Branch ID',
         'Branch Name', 'Credit Limit', 'Customer Sub Type', 'Billing Attention', 'Billing Address',
         'Billing Street2', 'Billing City', 'Billing State', 'Billing Country', 'Billing Code',
         'Billing Phone', 'Billing Fax', 'Shipping Attention', 'Shipping Address', 'Shipping Street2',
         'Shipping City', 'Shipping State', 'Shipping Country', 'Shipping Code', 'Shipping Phone',
         'Shipping Fax', 'Skype Identity', 'Facebook', 'Twitter', 'Department',
         'Designation', 'Price List', 'Payment Terms', 'Payment Terms Label', 'GST Treatment',
         'GST Identification Number (GSTIN)', 'PAN Number', 'Last Sync Time', 'Owner Name', 'Primary Contact ID',
         'EmailID', 'MobilePhone', 'Contact ID', 'Contact Name', 'Contact Type',
         'Place Of Contact', 'Place of Contact(With State Code)', 'Taxable', 'Tax Name', 'Tax Percentage',
         'Exemption Reason', 'Contact Address ID', 'Source', 'upload_status'])

    for row in reader:
        row_no += 1
        created_by = request.user
        created_time = row.get('Created Time')
        last_modified_time = row.get('Last Modified Time')
        display_name = row.get('Display Name')
        company_name = row.get('Company Name')
        salutation = row.get('Salutation')
        first_name = row.get('First Name')
        last_name = row.get('Last Name')
        phone = row.get('Phone')
        currency_code = row.get('Currency Code')
        notes = row.get('Notes')
        website = row.get('Website')
        status = row.get('Status')
        opening_balance = row.get('Opening Balance')
        exchange_rate = row.get('Exchange Rate')
        branch_id = row.get('Branch ID')
        branch_name = row.get('Branch Name')
        credit_limit = row.get('Credit Limit')
        customer_sub_type = row.get('Customer Sub Type')
        billing_attention = row.get('Billing Attention')
        billing_address = row.get('Billing Address')
        billing_street2 = row.get('Billing Street2')
        billing_city = row.get('Billing City')
        billing_state = row.get('Billing State')
        billing_country = row.get('Billing Country')
        billing_code = row.get('Billing Code')
        billing_phone = row.get('Billing Phone')
        billing_fax = row.get('Billing Fax')
        shipping_attention = row.get('Shipping Attention')
        shipping_address = row.get('Shipping Address')
        shipping_street2 = row.get('Shipping Street2')
        shipping_city = row.get('Shipping City')
        shipping_state = row.get('Shipping State')
        shipping_country = row.get('Shipping Country')
        shipping_code = row.get('Shipping Code')
        shipping_phone = row.get('Shipping Phone')
        shipping_fax = row.get('Shipping Fax')
        skype_identity = row.get('Skype Identity')
        facebook = row.get('Facebook')
        twitter = row.get('Twitter')
        department = row.get('Department')
        designation = row.get('Designation')
        price_list = row.get('Price List')
        payment_team = row.get('Payment Terms')
        payment_team_labs = row.get('Payment Terms Label')
        gst_treatment = row.get('GST Treatment')
        gst_identification_number = row.get('GST Identification Number (GSTIN)')
        pan_number = row.get('PAN Number')
        last_sync_time = row.get('Last Sync Time')
        owner_name = row.get('Owner Name')
        primary_contact_id = row.get('Primary Contact ID')
        email_id = row.get('EmailID')
        mobile_phone = row.get('MobilePhone')
        contact_id = row.get('Contact ID')
        contact_name = row.get('Contact Name')
        contact_type = row.get('Contact Type')
        place_of_contact = row.get('Place Of Contact')
        place_of_contact_with_state_code = row.get('Place of Contact(With State Code)')
        taxable = row.get('Taxable')
        tax_name = row.get('Tax Name')
        tax_percentage = row.get('Tax Percentage')
        exemption_reason = row.get('Exemption Reason')
        contact_address_id = row.get('Contact Address ID')
        source = row.get('Source')
        status_upload = ""
        if display_name:
            if not ZohoCustomers.objects.filter(display_name=display_name):
                try:
                    obj = ZohoCustomers.objects.create(created_by=created_by, created_time=created_time,
                                                       last_modified_time=last_modified_time, display_name=display_name,
                                                       company_name=company_name, salutation=salutation,
                                                       first_name=first_name, last_name=last_name, phone=phone,
                                                       currency_code=currency_code, notes=notes, website=website,
                                                       status=status, opening_balance=opening_balance,
                                                       exchange_rate=exchange_rate, branch_id=branch_id,
                                                       branch_name=branch_name, credit_limit=credit_limit,
                                                       customer_sub_type=customer_sub_type,
                                                       billing_attention=billing_attention, billing_address=billing_address,
                                                       billing_street2=billing_street2, billing_city=billing_city,
                                                       billing_state=billing_state, billing_country=billing_country,
                                                       billing_code=billing_code, billing_phone=billing_phone,
                                                       billing_fax=billing_fax, shipping_attention=shipping_attention,
                                                       shipping_address=shipping_address, shipping_street2=shipping_street2,
                                                       shipping_city=shipping_city, shipping_state=shipping_state,
                                                       shipping_country=shipping_country, shipping_code=shipping_code,
                                                       shipping_phone=shipping_phone, shipping_fax=shipping_fax,
                                                       skype_identity=skype_identity, facebook=facebook, twitter=twitter,
                                                       department=department, designation=designation,
                                                       price_list=price_list,
                                                       payment_team=payment_team, payment_team_labs=payment_team_labs,
                                                       gst_treatment=gst_treatment,
                                                       gst_identification_number=gst_identification_number,
                                                       pan_number=pan_number, last_sync_time=last_sync_time,
                                                       owner_name=owner_name, primary_contact_id=primary_contact_id,
                                                       email_id=email_id,
                                                       mobile_phone=mobile_phone, contact_id=contact_id,
                                                       contact_name=contact_name, contact_type=contact_type,
                                                       place_of_contact=place_of_contact,
                                                       place_of_contact_with_state_code=place_of_contact_with_state_code,
                                                       taxable=taxable, tax_name=tax_name, tax_percentage=tax_percentage,
                                                       exemption_reason=exemption_reason,
                                                       contact_address_id=contact_address_id, source=source
                                                       )
                    status_upload = 'success'
                except Exception as e:
                   status_upload = e
                
            else:
                status_upload = "Display Name  allready exists | error in row_no:{}".format(row_no)
        else:
            status_upload = "Display Name  can not be blank| error in row_no{}".format(row_no)
        writer.writerow(
            [created_time, last_modified_time, display_name, company_name, salutation, first_name, last_name, phone,
             currency_code, notes, website,
             status, opening_balance, exchange_rate, branch_id, branch_name, credit_limit,
             customer_sub_type, billing_attention, billing_address, billing_street2, billing_city,
             billing_state, billing_country, billing_code, billing_phone, billing_fax, shipping_attention,
             shipping_address, shipping_street2, shipping_city, shipping_state, shipping_country, shipping_code,
             shipping_phone, shipping_fax, skype_identity, facebook, twitter, department, designation, price_list,
             payment_team, payment_team_labs, gst_treatment, gst_identification_number, pan_number, last_sync_time,
             owner_name,
             primary_contact_id, email_id, mobile_phone, contact_id, contact_name, contact_type, place_of_contact,
             place_of_contact_with_state_code,
             taxable, tax_name, tax_percentage, exemption_reason, contact_address_id, source, status_upload])
    return response
