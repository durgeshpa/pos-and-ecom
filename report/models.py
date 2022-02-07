# -*- coding: utf-8 -*-
import time
from datetime import datetime, timedelta

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import (JSONField,
                                            ArrayField)
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from report.managers import (ScheduledReportRequestManager, 
                             AdHocReportRequestManager)
from report.validators import validate_input_params
# from report.utils import return_generator_function


def rid_generator(report_type, report_name):
    #print(report_type, report_name)
    return  report_type + ''.join(str(time.time()).split('.'))[:-2] + (report_name if report_name else 'RD')


class ReportChoice(models.Model):
    REPORT_SOURCES = (
        ('HT', 'Host'),
        ('RH', 'Redash')
    )
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
    source = models.CharField(choices=REPORT_SOURCES, 
                              max_length=10, 
                              default="HT")
    name = models.CharField(max_length=100)
    target_model = models.CharField(max_length=10, 
                                     choices=REPORT_CHOICES, 
                                     null=True, 
                                     blank=True)
    default_mappings = JSONField(null=True, 
                                 blank=True)
    required_mappings = JSONField(null=True, 
                                  blank=True)
    optional_mappings = JSONField(null=True, 
                                  blank=True)
    query_no = models.CharField(max_length=10, 
                                null=True, 
                                blank=True)
    token = models.CharField(max_length=50, 
                             null=True, 
                             blank=True)
    is_active = models.BooleanField(default=False)
    generator_function = models.CharField(max_length=100, 
                                          null=True, 
                                          blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def get_target_model(self):
        return self.target_model.model_class()
    
    def __str__(self) -> str:
        return str(self.id) + ' | ' + self.name
    
    def clean(self):
        super(ReportChoice, self).clean()
        errors = {}
        if not self.default_mappings and not self.required_mappings and not self.optional_mappings:
            errors['default_mappings'] = 'Mappings are required for report generation.'
            errors['required_mappings'] = 'Mappings are required for report generation.'
            errors['optional_mappings'] = 'Mappings are required for report generation.'
        if self.source == "HT": 
            if not self.generator_function:
                errors['generator_function'] = 'Required for source Host'
            if not self.target_model:
                errors['target_model'] = 'Required for source Host'
        if self.source == 'RH': 
            if not self.query_no:
                errors['query_no'] = 'Required for source Redash'
        raise ValidationError(errors)
    
    class Meta:
        verbose_name = "Report Choice"
        verbose_name_plural = "Report Choices"


class ReportRequest(models.Model):
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
    report_choice = models.ForeignKey(ReportChoice, 
                                      on_delete=models.DO_NOTHING, 
                                      related_name='report_requests',
                                      limit_choices_to={'is_active': True})
    report_type = models.CharField(choices=REPORT_TYPES,
                                   max_length=5)
    input_params = JSONField(null=False)
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
    failed_message = models.TextField(null=True, 
                                      blank=True)
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

        
    def clean(self):
        super(ReportRequest, self).clean()
        errors = {}
        if self.input_params and self.report_choice:
            input_params_errors = validate_input_params(self.input_params, self.report_choice.required_mappings)
            if input_params_errors:
                errors['input_params'] = input_params_errors
        raise ValidationError(errors)
        
    def save(self, *args, **kwargs):
        if not self.pk:
            self.rid = rid_generator(self.report_type, self.report_choice.target_model)
        return super(ReportRequest, self).save(*args, **kwargs)
    
    # def __str__(self) -> str:
    #     return self.rid

    class Meta:
        verbose_name = 'Report Request'
        verbose_name_plural = 'Report Requests'


class AdHocReportRequest(ReportRequest):
    objects = AdHocReportRequestManager()
    
    def clean(self):
       super(AdHocReportRequest, self).clean()
       errors = {}
       if self.frequency:
            errors['frequency'] = 'Frequency is not required for AdHoc type reports.'
       if self.schedule_time:
            errors['schedule_time'] = 'Schedule time is not required for AdHoc type reports.'
       raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.report_type = 'AD'
        if not self.pk:
            self.rid = rid_generator(self.report_type, self.report_choice.target_model)
        return super(AdHocReportRequest, self).save(*args, **kwargs)
    
    class Meta:
        proxy = True
        verbose_name = 'AdHoc Report Request'
        verbose_name_plural = 'AdHoc Report Requests'


class ScheduledReportRequest(ReportRequest):
    objects = ScheduledReportRequestManager()
    
    def clean(self):
        super(ScheduledReportRequest, self).clean()
        if self.frequency == "Daily":
            start = datetime.now() - timedelta(days=1)
        elif self.frequency in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
            start = datetime.now() - timedelta(days=7)
        else:
            start = datetime.now() - timedelta(days=30)
        self.input_params['date_start'] = start.strftime("%Y-%m-%d")
        errors = {}
        if not self.frequency:
            errors['frequency'] = 'Frequency is required for scheduled type reports.'
        if not self.schedule_time:
            errors['schedule_time'] = 'Schedule time is required for scheduled type reports.'
        raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.report_type = 'SC'
        
        if not self.pk:
            self.rid = rid_generator(self.report_type, self.report_choice.target_model)
        return super(ScheduledReportRequest, self).save(*args, **kwargs)
    
    class Meta:
        proxy = True
        verbose_name = 'Scheduled Report Request'
        verbose_name_plural = 'Scheduled Report Requests'


class ScheduledReport(models.Model):
    
    request = models.ForeignKey(ReportRequest, 
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
