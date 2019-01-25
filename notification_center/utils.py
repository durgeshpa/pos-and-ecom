import re

from notification_center.models import TemplateVariable, Template


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


