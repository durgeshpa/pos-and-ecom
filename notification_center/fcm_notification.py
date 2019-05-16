# from fcm.utils import get_device_model

# Device = get_device_model()


# class SendFCMNotification:
# 	# This class is used to send email to a list of users
# 	def __init__(self, registration_id, message_title=None, message_body=None):
# 		#super(SendEmail, self).__init__()
# 		#self.registration_ids = registration_ids
# 		self.registration_id = registration_id
# 		self.message_title = message_title or ""
# 		self.message_body = message_body or ""

# 	def send(self):
# 		try:
# 			#registration_ids = []
# 			print (self.registration_id, self.message_title, self.message_body)
# 			# my_phone = Device.objects.get(reg_id=self.registration_id)
# 			# my_phone.send_message({'message':self.message_body}, collapse_key='something')

# 		except:
# 			# print (traceback.format_exc(sys.exc_info()))
# 			if not self.fail_silently:
# 				raise