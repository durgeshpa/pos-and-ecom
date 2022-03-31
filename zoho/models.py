from django.contrib.auth import get_user_model
from django.db import models

# Create your models here.


class BaseTimestampUserModel(models.Model):
    """
        Abstract Model to have helper fields of created_at, created_by, updated_at and updated_by
    """
    created_at = models.DateTimeField(verbose_name="Created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="Updated at", auto_now=True)
    created_by = models.ForeignKey(
        get_user_model(), null=True,
        verbose_name="Created by",
        related_name="%(app_label)s_%(class)s_created_by",
        on_delete=models.DO_NOTHING
    )
    updated_by = models.ForeignKey(
        get_user_model(), null=True,
        verbose_name="Updated by",
        related_name="%(app_label)s_%(class)s_updated_by",
        on_delete=models.DO_NOTHING
    )

    class Meta:
        abstract = True


class ZohoFileUpload(BaseTimestampUserModel):
    CUSTOMER, INVOICE, CREDIT_NOTE = 'CUSTOMER', 'INVOICE', 'CREDIT_NOTE'
    UPLOAD_TYPE_CHOICES = (
        (CUSTOMER, 'Customer'),
        (INVOICE, 'Invoice'),
        (CREDIT_NOTE, 'Credit Note')
    )
    file = models.FileField(upload_to='zoho/zoho_files/')
    upload_type = models.CharField(max_length=50, null=True, choices=UPLOAD_TYPE_CHOICES)

    def __str__(self):
        return f"BulkUpload for Zoho File Upload updated at {self.created_at} by {self.updated_by}"


class ZohoCommonFields(models.Model):
    customer_id = models.CharField(max_length=100, null=True, blank=True)
    customer_name = models.CharField(max_length=100, null=True, blank=True)
    place_of_supply = models.TextField(null=True, blank=True)
    place_of_supply_with_state_code = models.CharField(max_length=100, null=True, blank=True)
    gst_treatment = models.CharField(max_length=100, null=True, blank=True)
    is_inclusive_tax = models.CharField(max_length=100, null=True, blank=True)
    currency_code = models.CharField(max_length=100, null=True, blank=True)
    exchange_rate = models.CharField(max_length=100, null=True, blank=True)
    discount_type = models.CharField(max_length=100, null=True, blank=True)
    is_discount_before_tax = models.CharField(max_length=100, null=True, blank=True)
    template_name = models.CharField(max_length=100, null=True, blank=True)
    entity_discount_percent = models.CharField(max_length=100, null=True, blank=True)
    tcs_tax_name = models.CharField(max_length=100, null=True, blank=True)
    tcs_percentage = models.CharField(max_length=100, null=True, blank=True)
    subtotal = models.CharField(max_length=100, null=True, blank=True)
    total = models.CharField(max_length=100, null=True, blank=True)
    balance = models.CharField(max_length=100, null=True, blank=True)
    adjustment = models.CharField(max_length=100, null=True, blank=True)
    adjustment_description = models.CharField(max_length=100, null=True, blank=True)
    notes = models.CharField(max_length=100, null=True, blank=True)
    terms_conditions = models.CharField(max_length=100, null=True, blank=True)
    e_invoice_status = models.CharField(max_length=100, null=True, blank=True)
    e_invoice_reference_number = models.CharField(max_length=100, null=True, blank=True)
    tcs_amount = models.CharField(max_length=100, null=True, blank=True)
    entity_discount_amount = models.CharField(max_length=100, null=True, blank=True)
    branch_id = models.CharField(max_length=100, null=True, blank=True)
    branch_name = models.CharField(max_length=100, null=True, blank=True)
    shipping_charge = models.CharField(max_length=100, null=True, blank=True)
    shipping_charge_tax_id = models.CharField(max_length=100, null=True, blank=True)
    shipping_charge_tax_amount = models.CharField(max_length=100, null=True, blank=True)
    shipping_charge_tax_name = models.CharField(max_length=100, null=True, blank=True)
    shipping_charge_tax_percentage = models.CharField(max_length=100, null=True, blank=True)
    shipping_charge_tax_type = models.CharField(max_length=100, null=True, blank=True)
    shipping_charge_tax_exemption_code = models.CharField(max_length=100, null=True, blank=True)
    shipping_charge_sac_code = models.CharField(max_length=100, null=True, blank=True)
    billing_attention = models.CharField(max_length=100, null=True, blank=True)
    billing_address = models.CharField(max_length=100, null=True, blank=True)
    billing_city = models.CharField(max_length=100, null=True, blank=True)
    billing_state = models.CharField(max_length=100, null=True, blank=True)
    billing_country = models.CharField(max_length=100, null=True, blank=True)
    billing_code = models.CharField(max_length=100, null=True, blank=True)
    billing_phone = models.CharField(max_length=100, null=True, blank=True)
    billing_fax = models.CharField(max_length=100, null=True, blank=True)
    shipping_attention = models.TextField(null=True, blank=True)
    shipping_address = models.TextField(null=True, blank=True)
    shipping_city = models.CharField(max_length=100, null=True, blank=True)
    shipping_state = models.CharField(max_length=100, null=True, blank=True)
    shipping_country = models.CharField(max_length=100, null=True, blank=True)
    shipping_code = models.CharField(max_length=100, null=True, blank=True)
    shipping_fax = models.CharField(max_length=100, null=True, blank=True)
    e_invoice_qrjson = models.CharField(max_length=100, null=True, blank=True)
    e_invoice_qr_raw_data = models.CharField(max_length=100, null=True, blank=True)
    e_invoice_ack_number = models.CharField(max_length=100, null=True, blank=True)
    e_invoice_ack_date = models.CharField(max_length=100, null=True, blank=True)
    e_invoice_cancel_remark = models.CharField(max_length=100, null=True, blank=True)
    e_invoice_cancel_reason = models.TextField(null=True, blank=True)
    e_invoice_failure_reason = models.TextField(null=True, blank=True)
    supplier_org_name = models.CharField(max_length=100, null=True, blank=True)
    supplier_gst_registration_number = models.CharField(max_length=100, null=True, blank=True)
    supplier_street_address = models.CharField(max_length=100, null=True, blank=True)
    supplier_city = models.CharField(max_length=100, null=True, blank=True)
    supplier_state = models.CharField(max_length=100, null=True, blank=True)
    supplier_country = models.CharField(max_length=100, null=True, blank=True)
    supplier_zipcode = models.CharField(max_length=100, null=True, blank=True)
    supplier_phone = models.CharField(max_length=100, null=True, blank=True)
    supplier_e_mail = models.CharField(max_length=100, null=True, blank=True)
    cgst_rate_percentage = models.CharField(max_length=100, null=True, blank=True)
    sgst_rate_percentage = models.CharField(max_length=100, null=True, blank=True)
    igst_rate_percentage = models.CharField(max_length=100, null=True, blank=True)
    cess_rate_percentage = models.CharField(max_length=100, null=True, blank=True)
    cgst_fcy = models.CharField(max_length=100, null=True, blank=True)
    sgst_fcy = models.CharField(max_length=100, null=True, blank=True)
    igst_fcy = models.CharField(max_length=100, null=True, blank=True)
    cess_fcy = models.CharField(max_length=100, null=True, blank=True)
    cgst = models.CharField(max_length=100, null=True, blank=True)
    sgst = models.CharField(max_length=100, null=True, blank=True)
    igst = models.CharField(max_length=100, null=True, blank=True)
    cess = models.CharField(max_length=100, null=True, blank=True)
    reverse_charge_tax_name = models.CharField(max_length=100, null=True, blank=True)
    reverse_charge_tax_rate = models.CharField(max_length=100, null=True, blank=True)
    reverse_charge_tax_type = models.CharField(max_length=100, null=True, blank=True)
    gst_identification_number_gstin = models.CharField(max_length=100, null=True, blank=True)
    nature_of_collection = models.CharField(max_length=100, null=True, blank=True)
    project_id = models.CharField(max_length=100, null=True, blank=True)
    project_name = models.CharField(max_length=100, null=True, blank=True)
    hsn_sac = models.CharField(max_length=100, null=True, blank=True)
    round_off = models.CharField(max_length=100, null=True, blank=True)
    sales_person = models.CharField(max_length=100, null=True, blank=True)
    subject = models.CharField(max_length=100, null=True, blank=True)
    reference_invoice_type = models.CharField(max_length=100, null=True, blank=True)
    account = models.CharField(max_length=100, null=True, blank=True)
    account_code = models.CharField(max_length=100, null=True, blank=True)
    supply_type = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        abstract = True


class ZohoCommonItemFields(models.Model):
    usage_unit = models.CharField(max_length=100, null=True, blank=True)
    item_price = models.CharField(max_length=100, null=True, blank=True)
    item_type = models.CharField(max_length=100, null=True, blank=True)
    item_tax = models.CharField(max_length=100, null=True, blank=True)
    item_tax_percentage = models.CharField(max_length=100, null=True, blank=True)
    item_tax_type = models.CharField(max_length=100, null=True, blank=True)
    item_tax_exemption_reason = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        abstract = True


class ZohoCreditNote(ZohoCommonFields):
    credit_note_number = models.CharField(max_length=100, null=True, blank=True)
    credit_note_status = models.CharField(max_length=100, null=True, blank=True)
    billing_street_2 = models.CharField(max_length=100, null=True, blank=True)
    shipping_street_2 = models.CharField(max_length=100, null=True, blank=True)
    shipping_phone = models.CharField(max_length=100, null=True, blank=True)
    reference = models.CharField(max_length=100, null=True, blank=True)
    associated_invoice_number = models.CharField(max_length=100, null=True, blank=True)
    associated_invoice_date = models.CharField(max_length=100, null=True, blank=True)
    applied_invoice_number = models.CharField(max_length=100, null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    tax1_id = models.CharField(max_length=100, null=True, blank=True)


class ZohoCreditNoteItem(ZohoCommonItemFields):
    zoho_credit_note = models.ForeignKey(ZohoCreditNote, on_delete=models.CASCADE)
    tax1_id = models.CharField(max_length=100, null=True, blank=True)


class ZohoInvoice(ZohoCommonFields):
    invoice_date = models.CharField(max_length=100, null=True, blank=True)
    invoice_id = models.CharField(max_length=100, null=True, blank=True)
    invoice_number = models.CharField(max_length=100, null=True, blank=True)
    invoice_status = models.CharField(max_length=100, null=True, blank=True)
    due_date = models.CharField(max_length=100, null=True, blank=True)
    purchaseorder = models.CharField(max_length=100, null=True, blank=True)
    expected_payment_date = models.CharField(max_length=100, null=True, blank=True)
    last_payment_date = models.CharField(max_length=100, null=True, blank=True)
    payment_terms = models.CharField(max_length=100, null=True, blank=True)
    payment_terms_label = models.CharField(max_length=100, null=True, blank=True)
    sales_order_number = models.CharField(max_length=100, null=True, blank=True)
    expense_reference_id = models.CharField(max_length=100, null=True, blank=True)
    recurrence_name = models.CharField(max_length=100, null=True, blank=True)
    paypal = models.CharField(max_length=100, null=True, blank=True)
    authorize_net = models.CharField(max_length=100, null=True, blank=True)
    google_checkout = models.CharField(max_length=100, null=True, blank=True)
    payflow_pro = models.CharField(max_length=100, null=True, blank=True)
    stripe = models.CharField(max_length=100, null=True, blank=True)
    paytm = models.CharField(max_length=100, null=True, blank=True)
    checkout = models.CharField(max_length=100, null=True, blank=True)
    braintree = models.CharField(max_length=100, null=True, blank=True)
    forte = models.CharField(max_length=100, null=True, blank=True)
    worldpay = models.CharField(max_length=100, null=True, blank=True)
    payments_pro = models.CharField(max_length=100, null=True, blank=True)
    square = models.CharField(max_length=100, null=True, blank=True)
    wepay = models.CharField(max_length=100, null=True, blank=True)
    razorpay = models.CharField(max_length=100, null=True, blank=True)
    gocardless = models.CharField(max_length=100, null=True, blank=True)
    partial_payments = models.CharField(max_length=100, null=True, blank=True)
    billing_street2 = models.CharField(max_length=100, null=True, blank=True)
    shipping_street2 = models.CharField(max_length=100, null=True, blank=True)
    shipping_phone_number = models.CharField(max_length=100, null=True, blank=True)
    primary_contact_emailid = models.CharField(max_length=100, null=True, blank=True)
    primary_contact_mobile = models.CharField(max_length=100, null=True, blank=True)
    primary_contact_phone = models.CharField(max_length=100, null=True, blank=True)
    estimate_number = models.CharField(max_length=100, null=True, blank=True)
    custom_charges = models.CharField(max_length=100, null=True, blank=True)
    shipping_bill = models.CharField(max_length=100, null=True, blank=True)
    shipping_bill_date = models.CharField(max_length=100, null=True, blank=True)
    shipping_bill_total = models.CharField(max_length=100, null=True, blank=True)
    portcode = models.CharField(max_length=100, null=True, blank=True)
    reference_invoice = models.CharField(max_length=100, null=True, blank=True)
    reference_invoice_date = models.CharField(max_length=100, null=True, blank=True)
    gst_registration_number_reference_invoice = models.CharField(max_length=100, null=True, blank=True)
    reason_for_issuing_debit_note = models.CharField(max_length=100, null=True, blank=True)
    e_commerce_operator_name = models.CharField(max_length=100, null=True, blank=True)
    e_commerce_operator_gstin = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return str(self.invoice_id) + str(self.invoice_number)


class ZohoInvoiceItem(ZohoCommonItemFields):
    zoho_invoice = models.ForeignKey(ZohoInvoice, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=100, null=True, blank=True)
    item_desc = models.TextField(null=True, blank=True)
    quantity = models.CharField(max_length=100, null=True, blank=True)
    discount = models.CharField(max_length=100, null=True, blank=True)
    discount_amount = models.CharField(max_length=100, null=True, blank=True)
    item_total = models.CharField(max_length=100, null=True, blank=True)
    product_id = models.CharField(max_length=100, null=True, blank=True)
    tax_id = models.CharField(max_length=100, null=True, blank=True)
    item_tax_amount = models.CharField(max_length=100, null=True, blank=True)


# class ZohoCustomers(models.Model):
#     pass

