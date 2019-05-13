import sys
import traceback

from django.conf import settings
from django.core.mail import EmailMessage


class SendEmail(object):
	# This class is used to send email to a list of users
	def __init__(self):
		super(SendEmail, self).__init__()
		self.email_list = email_list
		self.from_email = from_email
		self.email_body = email_body
		self.subject = subject
		self.cc_email = [cc_email]

	def send(self):
		try:
			msg = EmailMessage(subject, email_body, from_email, email_list, cc_email)
			msg.content_subtype = settings.MIME_TYPE

			# Add attachment to the email if any
			if attachment != '':
				msg.add_file(attachment)

			msg.send()
		except:
			# print (traceback.format_exc(sys.exc_info()))
			if not self.fail_silently:
				raise