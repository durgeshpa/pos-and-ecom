from django.db import models


class MailRecipient(models.Model):
    """
        Contains email
    """
    mail_address = models.EmailField(max_length=254)

    def __str__(self):
        return self.mail_address


class RedashScheduledReport(models.Model):
    """
        Contains subject body recipients and cron expression,to evaluate when the email has to be sent
    """
    csv_url = models.URLField(max_length=200)
    recipients_list = models.ManyToManyField(MailRecipient, related_name='mail_list')
    subject = models.CharField(max_length=200)
    body = models.CharField(max_length=200)
    date_time = models.DateTimeField()

    def __str__(self):
        return self.subject
