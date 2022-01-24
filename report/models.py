# -*- coding: utf-8 -*-

import random
from tabnanny import verbose
import time

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import (JSONField,
                                            ArrayField)
from django.core.exceptions import ValidationError
from report.managers import ScheduledReportRequestManager

def rid_generator(report_type, report_name):
    return  report_type + ''.join(str(time.time()).split('.'))[:-2] + report_name

class AsyncReportRequest(models.Model):

    REPORT_CHOICES = (
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
    REPORT_SOURCES = (
        ('HT', 'Host'),
        ('RH', 'Redash')
    )
    REPORT_TYPES = (
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
        ('P', 'Proccessing'),
        ('S', 'Success'),
        ('F', 'Failed'),
        ('EF', 'Email Failed')
    )
    
    rid = models.CharField(max_length=50,
                           null=True,
                           blank=True)
    input_params = JSONField(null=True)
    report_name = models.CharField(choices=REPORT_CHOICES,
                                   max_length=5)
    report_type = models.CharField(choices=REPORT_TYPES,
                                   max_length=5, 
                                   default='AD')
    source = models.CharField(choices=REPORT_SOURCES, 
                                   max_length=5, default='HT')
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
                        blank=True, default=list)
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
            self.rid = rid_generator(self.report_type, self.report_name)
        return super().save(*args, **kwargs)
        
    def clean(self):
        super(AsyncReportRequest, self).clean()
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
    
    def __str__(self) -> str:
        return self.rid

    class Meta:
        verbose_name = 'Async Report Request'
        verbose_name_plural = 'Async Report Requests'


class ScheduledReportRequest(AsyncReportRequest):
    objects = ScheduledReportRequestManager()
    
    class Meta:
        proxy = True
        verbose_name = 'Scheduled Report Request'
        verbose_name_plural = 'Scheduled Report Requests'


class ScheduledReport(models.Model):
    
    request = models.ForeignKey(AsyncReportRequest, 
                                on_delete=models.CASCADE, 
                                related_name='reports')
    report = models.FileField(upload_to='reports/csv/',
                              null=True,
                              blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self) -> str:
        return str(self.id) + " | " + str(self.request)
    
    class Meta:
        verbose_name = 'Scheduled Report'
        verbose_name_plural = 'Scheduled Reports'
