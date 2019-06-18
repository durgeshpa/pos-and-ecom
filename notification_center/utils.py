import re
import logging

from fcm.utils import get_device_model
from django.template import Context, Template as DjangoTemplate
#from django.contrib.auth import get_user_model
from django.conf import settings

from otp.sms import SendSms
from notification_center.fcm_notification import SendFCMNotification

from notification_center.models import TemplateVariable, Template, UserNotification
from gram_to_brand.models import Cart
from shops.models import Shop, ParentRetailerMapping

#User = get_user_model()
Device = get_device_model()

logger = logging.getLogger(__name__)


class GenerateTemplateData:
    # This class will geneate template data
    # Input: transaction type, user_id and
    # Output: A dictionary containing the template data
    def __init__(self, user_id="", transaction_type="", transaction_data={}):
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
        # order_no,items_count, total_amount, shop_name
        pass

    def generate_order_received_action_data(self):
        pass
        # order_id = self.transaction_data['order_id']
            # order = Order.objects.get(id=order_id)        
        # self.template_data['order_number'] = order.order_number
        # self.template_data['order_status'] = order.order_status    

    def generate_shop_verified_action_data(self):
        pass
        # shop_id = self.transaction_data['shop_id']
        # shop = Shop.objects.get(id=shop_id)        
        # self.template_data['shop_title'] = str(shop.shop_name)

    def generate_po_approved_data(self):
        cart = Cart.objects.get(id=cart_id)
        self.template_data['po_number'] = cart.po_no
        self.template_data['po_creation_date'] = cart.po_creation_date

    def generate_po_created_data(self):
        cart = Cart.objects.get(id=cart_id)
        self.template_data['po_number'] = cart.po_no
        self.template_data['po_creation_date'] = cart.po_creation_date
        
    def generate_po_edited_data(self):
        cart = Cart.objects.get(id=cart_id)
        self.template_data['po_number'] = cart.po_no
        self.template_data['po_creation_date'] = cart.po_creation_date

    def create(self):
        self.generate_common_data()
        if self.transaction_type == "SIGNUP":
            self.generate_signup_action_data()
        
        elif self.transaction_type == "ORDER_CREATED":
            self.generate_order_created_action_data()
        
        elif self.transaction_type == "ORDER_RECEIVED":
            self.generate_order_received_action_data()

        elif self.transaction_type == "SHOP_VERIFIED":
            self.generate_shop_verified_action_data()
        
        elif self.transaction_type == "PO_APPROVED":
            self.generate_po_approved_data()
        
        elif self.transaction_type == "PO_CREATED":
            self.generate_po_created_data()        
        
        elif self.transaction_type == "PO_EDITED":
            self.generate_po_edited_data()    

        return self.template_data


class SendNotification:
    # This class will be used for sending the notifications to users
    def __init__(self, 
            user_id="", 
            activity_type="",
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

    def send_to_a_group(self):
        # fetch the group and location and call send for each user specifically
        #import pdb; pdb.set_trace()
        template = Template.objects.get(type=self.template_type)
        notification_groups = template.notification_groups.all()
        shop = ParentRetailerMapping.objects.get(retailer_id=self.data['shop_id']).parent        
        #shop = Shop.objects.get(id=self.data['shop_id'])
        #shop = Shop.objects.filter(get_shop_city=self.data['city'],shop_name="GramFactory")
        
        # users of the shop for our campaign        
        for group in notification_groups:
            users = shop.related_users.filter(groups=group)

            # notification_groups for the shop location
            self.template_data = GenerateTemplateData(
                transaction_type=self.template_type,
                transaction_data=self.data).create()
           
            self.template_data = {**self.template_data, **self.data}

            sms_content = self.merge_template_with_data(template.text_sms_template)

            for user in users:
                user_id = user.id
                # generate template variable data
                print (user.phone_number, sms_content)
                # message = SendSms(phone=user.phone_number, body=sms_content)
                # # message = SendSms(phone=9643112048,body="Dear sagar, You have successfully signed up in GramFactory, India's No. 1 Retailers' App for ordering. Thanks, Team GramFactory")
                # message.send()

    def send(self):
        try:
            #import pdb; pdb.set_trace()
            #generate template content
            template = Template.objects.get(type=self.template_type)
 
            # generate template variable data
            self.template_data = GenerateTemplateData(self.user_id, self.template_type, self.data).create()#.generate_data()
            #self.template_data['username'] = self.data['username']
            
            self.template_data = {**self.template_data, **self.data}
            # if notification_types.email_notification:
            #     email_content = merge_template_with_data(template.text_email_template, self.email_variable)
            #     email = SendEmail()
            #     email.send()

            # if notification_types.app_notification:

            # fetch user registration id

            reg_id = Device.objects.get(user_id=self.user_id).reg_id #(name="Sagar").reg_id
            message_title = template.gcm_title
            message_body = self.merge_template_with_data(template.gcm_description)
            # sms_content = self.merge_template_with_data("Dear {{ username }}, You have successfully signed up in GramFactory, India's No. 1 Retailers' App for ordering. Thanks, Team GramFactory", self.sms_variable)
            notification = SendFCMNotification(
                registration_id=reg_id,
                message_title=message_title,
                message_body=message_body
                )            
            notification.send()

            # if notification_types.sms_notification:

            # sms_content = self.merge_template_with_data(template.text_sms_template)
            # #print (self.data['phone_number'], sms_content)
            # logging.info(self.data['phone_number'], sms_content)
            # # sms_content = self.merge_template_with_data("Dear {{ username }}, You have successfully signed up in GramFactory, India's No. 1 Retailers' App for ordering. Thanks, Team GramFactory", self.sms_variable)
            # message = SendSms(phone=self.data['phone_number'], body=sms_content)
            # # message = SendSms(phone="9643112048",
            #           body="Dear %s, Your Shop %s has been approved. Click here to start ordering immediately at GramFactory App." \
            #                " Thanks," \
            #                " Team GramFactory " % ("sagar", "saggy-shop"))
            # message.send()

        except Exception as e:
            # print (str(e))
            logging.error(str(e))    


def test():
    activity_type = "SHOP_VERIFIED" #SHOP_VERIFIED
    user_id = 1 #self.shop_owner.id
    data = {}
    data['username'] = "sagar" #username
    data['phone_number'] = "9643112048" #self.shop_owner.phone_number
    data['shop_title'] = "saggy-shop" #shop_title

    #from notification_center.utils import SendNotification
    SendNotification(user_id=user_id, activity_type=activity_type, data=data).send()    
    # message = SendSms(phone="9643112048",
    #                   body="Dear %s, Your Shop %s has been approved. Click here to start ordering immediately at GramFactory App." \
    #                        " Thanks," \
    #                        " Team GramFactory " % ("sagar", "saggy-shop"))
    # message.send()
