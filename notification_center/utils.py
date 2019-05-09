import re

from django.template import Context, Template
from django.contrib.auth import get_user_model

from otp.sms import SendSms
from notification_center.models import TemplateVariable, Template

User = get_user_model()


class GenerateTemplateData:
    # This class will geneate template data
    # Input: transaction type, user_id and
    # Output: A dictionary containing the template data
    def __init__(self, user_id, transaction_type, transaction_data):
        self.user_id = user_id
        self.transaction_type = transaction_type
        self.transaction_data = transaction_data
        self.template_data = {}

    def generate_common_data(self):
        self.template_data['username'] = User.objects.get(id=user_id)

    def generate_signup_action_data(self):
        # self.template_data['username'] = User.objects.get(id=user_id)        
        self.template_data['otp'] = ""
        self.template_data['time_limit'] = 5 #time limit for otp expiry

    def generate_order_created_action_data(self):
        order_id = self.transaction_data['order_id']
        order = Order.objects.get(id=order_id)        
        self.template_data['order_number'] = order.order_number
        self.template_data['order_status'] = order.order_status

    def create(self):
        generate_common_data()
        if self.transaction_type == "SIGNUP":
            generate_signup_action_data()
        elif self.transaction_type == "ORDER_CREATED":
            generate_order_created_action_data()    



class GetTemplateVariables:
    def __init__(self, template):
        self.template = template
        self.data = {
            'email_variable': None,
            'text_sms_variable': None,
            'voice_call_variable': None,
            'gcm_variable': None
        }

    def create(self):
        """Create or Update TemplateVariable object

        Getting template as argument, finding active notification type,
        searching through the text and storing variables in TemplateVariable
        """
        if self.template.email_alert:
            email_variable = self.get_template_variables(
                self.template.text_email_template
            )
            self.data.update(email_variable=email_variable)
        if self.template.text_sms_alert:
            text_sms_variable = self.get_template_variables(
                self.template.text_sms_template
            )
            self.data.update(text_sms_variable=text_sms_variable)
        if self.template.voice_call_alert:
            voice_call_variable = self.get_template_variables(
                self.template.voice_call_template
            )
            self.data.update(voice_call_variable=voice_call_variable)
        if self.template.gcm_alert:
            gcm_variable = self.get_template_variables(
                self.template.gcm_description
            )
            sellf.data.update(gcm_variable=gcm_variable)

        # to create or update the TemplateVariable object
        TemplateVariable.objects.update_or_create(
            template=self.template, defaults=self.data)

    @staticmethod
    def get_template_variables(text):
        """Return list of variables in template

        Variables should be in < > e.g <first_name>
        """
        variables = re.findall("\<(.*?)\>", text)
        return variables


class SendNotification:
    # This class will be used for sending the notifications to users
    def __init__(self, 
            user_id, 
            user_id_list = [],
            email_variable={}, 
            sms_variable={}, 
            app_notification_variable={}):
        
        self.user_id_list = user_id_list
        self.user_id = user_id
        self.template_type = activity_type
        self.email_variable = email_variable
        
        # self.data = {
        #     'email_variable': None,
        #     'text_sms_variable': None,
        #     'voice_call_variable': None,
        #     'gcm_variable': None
        # } 

    def fetch_notification_types(self):
        pass

    def merge_template_with_data(self, template, template_data):
        if template is not None:
            template = Template(template)
    
        return template.render(Context(self.template_data))


    def create(self):
        # This function will send the notifications(email, sms, fcm) to users 
        notification_types  = UserNotification.objects.filter(user=user_id)
        template = Template.objects.filter(template_type=self.template_type)

        if notification_types.email_notification:
            email_content = merge_template_with_data(template.text_email_template, self.email_variable)
            send_email()

        if notification_types.sms_notification:
            sms_content = merge_template_with_data(template.text_sms_template, self.sms_variable)
            message = SendSms(phone=9643112048,body="Dear sagar, You have successfully signed up in GramFactory, India's No. 1 Retailers' App for ordering. Thanks, Team GramFactory")
            message.send()