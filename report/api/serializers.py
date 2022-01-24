# -*- coding: utf-8 -*-

from distutils.log import error
from django.contrib.auth import get_user_model
from rest_framework import serializers

from report.models import AsyncReportRequest, ScheduledReport
from report.api.validators import validate_host_input_params, validate_redash_input_params
from report.utils import set_host_input_params, set_redash_input_params


class AsyncReportModelSerializer(serializers.ModelSerializer):
    
    def validate(self, data):
        super().validate(data)
        errors = {}
        if not self.instance:
            if data.get('report_type') == 'SC':
                if not data.get('schedule_time'):
                    errors['schedule_time'] = 'Scheduled time is required for scheduling reports.'
                if not data.get('frequency'):
                    errors['frequency'] = 'Frequency is required for scheduling reports.'
            else:
                pass
            if data.get('source', 'HT') == 'HT':
                errors = validate_host_input_params(data.get('report_name'), 
                                                    data.get('input_params'), 
                                                    errors,
                                                    data.get('report_type'))
                if errors:
                    raise serializers.ValidationError(errors)
                else:
                    data['input_params'] = set_host_input_params(data.get('report_name'), 
                                                                 data.get('input_params'), 
                                                                 data.get('report_type'), 
                                                                 data.get('frequency'))
                    return data
            else:
                errors = validate_redash_input_params(data.get('report_name'), 
                                                      data.get('input_params'), 
                                                      errors, 
                                                      data.get('report_type'))
                if errors:
                    raise serializers.ValidationError(errors)
                else:
                    data['input_params'] = set_redash_input_params(data.get('report_name'), 
                                                                   data.get('input_params'))
                    return data
        else:
            pass
        
    
    class Meta:
        model = AsyncReportRequest
        fields = ('id', 'input_params', 'source',
                  'report_name', 'report_type',
                  'status', 'report', 'user',
                  'emails', 'frequency', 'schedule_time')


class UserMetaModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = get_user_model()
        fields = ('id', 'email', 'first_name', 'last_name', 'phone_number')


class ScheduledReportMetaSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ScheduledReport
        fields = ('report', 'created_at')


class AsyncReportListSerializer(serializers.ModelSerializer):
    STATUS = {
        item[0] : item[1]
        for item in AsyncReportRequest.STATUS
    }
    REPORT_TYPE = {
        item[0] : item[1]
        for item in AsyncReportRequest.REPORT_TYPES
    }
    REPORT_CHOICE = {
        item[0] : item[1]
        for item in AsyncReportRequest.REPORT_CHOICES
    }
    emails = serializers.ListField(child=serializers.EmailField(max_length=100,
                                                                allow_blank=False),
                                   allow_empty=True)
    user = UserMetaModelSerializer(read_only=True)
    status = serializers.SerializerMethodField()
    report_type = serializers.SerializerMethodField()
    report_name = serializers.SerializerMethodField()
    scheduled_reports = serializers.SerializerMethodField()
    
    def get_report_type(self, instance):
        return AsyncReportListSerializer.REPORT_TYPE.get(instance.report_type)
    
    def get_status(self, instance):
        return AsyncReportListSerializer.STATUS.get(instance.status)

    def get_report_name(self, instance):
        return AsyncReportListSerializer.REPORT_CHOICE.get(instance.report_name)
    
    def get_scheduled_reports(self, instance):
        if instance.report_type == 'SC':
            return ScheduledReportMetaSerializer(instance.reports.all(), many=True).data
        else:
            return None
    
    class Meta:
        model = AsyncReportRequest
        fields = ('id', 'rid', 'status',
                  'report_type', 'report_name', 
                  'user', 'report', 'emails', 'scheduled_reports')


class AsyncReportRetrieveSerializer(AsyncReportListSerializer):
    
    class Meta:
        model = AsyncReportRequest
        exclude = ('input_params',)