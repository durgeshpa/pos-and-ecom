from django.db import models


class RedashScheduledReport(models.Model):
    """
        Contains subject body recipients and cron expression,to evaluate when the email has to be sent
    """

    FREQUENCY_CHOICES = (
        ('Daily', 'Daily'),
        ('Weekly', (
            ('Monday', 'Monday'),
            ('Tuesday', 'Tuesday'),
            ('Wednesday', 'Wednesday'),
            ('Thursday', 'Thursday'),
            ('Friday', 'Friday'),
            ('Saturday', 'Saturday'),
            ('Sunday', 'Sunday'),
        )
        ),
        ('Monthly', (
            ('1', '1'),
            ('2', '2'),
            ('3', '3'),
            ('4', '4'),
            ('5', '5'),
            ('6', '6'),
            ('7', '7'),
            ('8', '8'),
            ('9', '9'),
            ('10', '10'),
            ('11', '11'),
            ('12', '12'),
            ('13', '13'),
            ('14', '14'),
            ('15', '15'),
            ('16', '16'),
            ('17', '17'),
            ('18', '18'),
            ('19', '19'),
            ('20', '20'),
            ('21', '21'),
            ('22', '22'),
            ('23', '23'),
            ('24', '24'),
            ('25', '25'),
            ('26', '26'),
            ('27', '27'),
            ('28', '28'),
            ('29', '29'),
            ('30', '30'),
            ('31', '31'),
        )
        ),
    )
    csv_url = models.URLField(max_length=200)
    recipients = models.TextField(max_length=100)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField(max_length=200, blank=True)
    schedule = models.CharField(max_length=50, choices=FREQUENCY_CHOICES)
    # time = models.TimeField()

    def __str__(self):
        return self.subject



