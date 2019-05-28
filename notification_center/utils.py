import re
#from fcm.utils import get_device_model
import logging

from django.template import Context, Template as DjangoTemplate
#from django.contrib.auth import get_user_model
from django.conf import settings

from otp.sms import SendSms
#from notification_center.fcm_notification import SendFCMNotification

from notification_center.models import TemplateVariable, Template, UserNotification
#from notification_center.views import fetch_user_data 

#User = get_user_model()
#Device = get_device_model()

logger = logging.getLogger(__name__)


class GenerateTemplateData:
    # This class will geneate template data
    # Input: transaction type, user_id and
    # Output: A dictionary containing the template data
    def __init__(self, user_id, transaction_type, transaction_data={}):
        self.user_id = user_id
        self.transaction_type = transaction_type
        self.transaction_data = transaction_data
        self.template_data = {}

    def generate_common_data(self):
        #self.template_data['username'] = User.objects.get(id=self.user_id).first_name
        pass

    def generate_signup_action_data(self):
        # self.template_data['username'] = User.objects.get(id=user_id)        
        self.template_data['otp'] = ""
        self.template_data['time_limit'] = 5 #time limit for otp expiry

    def generate_order_created_action_data(self):
        pass
        # order_id = self.transaction_data['order_id']
        # order = Order.objects.get(id=order_id)        
        # self.template_data['order_number'] = order.order_number
        # self.template_data['order_status'] = order.order_status

    def create(self):
        self.generate_common_data()
        if self.transaction_type == "SIGNUP":
            self.generate_signup_action_data()
        elif self.transaction_type == "ORDER_CREATED":
            self.generate_order_created_action_data()    
        return self.template_data


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
            self.data.update(gcm_variable=gcm_variable)

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
            activity_type,
            data = {},
            user_id_list=[],
            email_variable={}, 
            sms_variable={}, 
            app_notification_variable={}):
        
        self.user_id_list = user_id_list
        self.user_id = user_id
        self.template_type = activity_type
        self.email_variable = email_variable
        self.sms_variable = {}
        self.data = data

    def fetch_notification_types(self):
        pass

    def merge_template_with_data(self, template_content=""):
        #import pdb; pdb.set_trace()
        final_template = DjangoTemplate(template_content)

        # if template_content is not None:
        #     final_template = DjangoTemplate(template_content)
        
        return final_template.render(Context(self.template_data))


    def send(self):
        try:
            # import pdb; pdb.set_trace()
            # This function will send the notifications(email, sms, fcm) to users 
            user_data = self.data #fetch_user_data(self.user_id)        
            #user = User.objects.get(id=self.user_id)
            # notification_types  = UserNotification.objects.get_or_create(user=user)
            
            #generate template content
            template = Template.objects.get(type=self.template_type)

            # generate template variable data
            self.template_data = GenerateTemplateData(self.user_id, self.template_type).create()#.generate_data()
            self.template_data['username'] = self.data['username']
            # if notification_types.email_notification:
            #     email_content = merge_template_with_data(template.text_email_template, self.email_variable)
            #     email = SendEmail()
            #     email.send()

            # if notification_types.app_notification:

            #     # fetch user registration id
            #     reg_id = Device.objects.get(name="Sagar").reg_id
            #     message_title = template.gcm_title
            #     message_body = self.merge_template_with_data(template.gcm_description)
            #     # sms_content = self.merge_template_with_data("Dear {{ username }}, You have successfully signed up in GramFactory, India's No. 1 Retailers' App for ordering. Thanks, Team GramFactory", self.sms_variable)
            #     notification = SendFCMNotification(
            #         registration_id=reg_id,
            #         message_title=message_title,
            #         message_body=message_body
            #         )            
            #     notification.send()

            # if notification_types.sms_notification:

            sms_content = self.merge_template_with_data(template.text_sms_template)
            print (self.data['phone_number'], sms_content)
            logging.info(self.data['phone_number'], sms_content)
            # sms_content = self.merge_template_with_data("Dear {{ username }}, You have successfully signed up in GramFactory, India's No. 1 Retailers' App for ordering. Thanks, Team GramFactory", self.sms_variable)
            # message = SendSms(phone=self.data['phone_number'], body=sms_content)
            # # message = SendSms(phone=9643112048,body="Dear sagar, You have successfully signed up in GramFactory, India's No. 1 Retailers' App for ordering. Thanks, Team GramFactory")
            # message.send()
        except Exception as e:
            # print (str(e))
            logging.error(str(e))    