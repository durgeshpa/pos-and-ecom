# -*- coding: utf-8 -*-

import random
import time

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import (JSONField,
                                            ArrayField)
from django.core.exceptions import ValidationError

def rid_generator(self):
    return  self.report_type + ''.join(str(time.time()).split('.'))[:-2] + self.report_name

class AsyncReport(models.Model):

    REPORT_CHOICE = (
        ('EO', 'Ecom - Orders'),
        ('BO', 'Buyer - Orders'),
        ('BP', 'Buyer - Payements'),
        ('BR', 'Buyer - Returns'),
        ('IC', 'Inventory Changes'),
        ('SGR', 'Store - GRN - Returns'),
        ('SG', 'Store - GRNs'),
        ('SP', 'Store - POs'),
        ('O', 'Order'),
        ('C', 'Commercial'),
        ('CC', 'Customer Care'),
    )
    REPORT_TYPE = (
        ('AD', 'AdHoc'),
        ('SC', 'Scheduled')
    )
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
    STATUS = (
        ('N', 'New'),
        ('S', 'Success'),
        ('F', 'Failed'),
        ('EF', 'Email Failed')
    )
    
    rid = models.CharField(max_length=50,
                           null=True,
                           blank=True)
    input_params = JSONField(null=True)
    report_name = models.CharField(choices=REPORT_CHOICE,
                                   max_length=5)
    report_type = models.CharField(choices=REPORT_TYPE,
                                   max_length=5,
                                   default='AD')
    status = models.CharField(choices=STATUS,
                             max_length=3, 
                             default='N')
    report = models.FileField(upload_to='reports/csv/',
                              null=True,
                              blank=True)
    user = models.ForeignKey(get_user_model(),
                             related_name='async_reports',
                             null=True,
                             blank=True,
                             on_delete=models.DO_NOTHING)
    emails = ArrayField(models.EmailField(max_length=100),
                        blank=True, default=[])
    frequency = models.CharField(choices=FREQUENCY_CHOICES,
                                 max_length=12, 
                                 null=True, 
                                 blank=True)
    schedule_time = models.TimeField(null=True,
                                     blank=True)
    report_created_at = models.DateTimeField(null=True,
                                             blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.pk:
            self.rid = rid_generator(self)
        return super().save(*args, **kwargs)
        
    def clean(self):
        super(AsyncReport, self).clean()
        if self.report_type == 'SC':
            if not self.frequency:
                raise ValidationError({'frequency': 'Frequency is required for scheduled type reports.'})
            if not self.schedule_time:
                raise ValidationError({'schedule_time': 'Schedule time is required for scheduled type reports.'})
        else:
            if self.frequency:
                raise ValidationError({'frequency': 'Frequency is not required for AdHoc type reports.'})
            if self.schedule_time:
                raise ValidationError({'schedule_time': 'Schedule time is not required for AdHoc type reports.'})
    
    def __str__(self):
        return self.rid

    class Meta:
        verbose_name = 'Async Report'
        verbose_name_plural = 'Async Reports'