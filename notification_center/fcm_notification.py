import sys
import traceback

from fcm.utils import get_device_model

Device = get_device_model()


class SendFCMNotification:
	# This class is used to send email to a list of users
	def __init__(self, registration_id="", message_title=None, message_image=None, message_body=None):
		#super(SendEmail, self).__init__()
		#self.registration_ids = registration_ids
		self.registration_id = registration_id
		self.message_title = message_title or ""
		self.message_image = message_image or ""
		self.message_body = message_body or ""

	def send_to_all(self):
		try:
			#registration_ids = []
			#print (self.registration_id, self.message_title, self.message_body)
			# devices = Device.objects.all()
			# devices.send_message({'message':self.message_body}, collapse_key='something')
			Device.objects.all().send_message({'message':'my test message'})

		except Exception as e:
			print (traceback.format_exc(sys.exc_info()))
			print (e)

	def send(self):
		try:
			#registration_ids = []
			# print (self.registration_id, self.message_title, self.message_body)
			my_phone = Device.objects.get(reg_id=self.registration_id)
			my_phone.send_message({'message':self.message_body,
									#'image':self.message_image,
									'title':self.message_title

				}, collapse_key='something')

		except Exception as e:
			print (traceback.format_exc(sys.exc_info()))
			print (e)
