# -*- coding: utf-8 -*-

from django.contrib.auth import get_user_model
from rest_framework import serializers

from report.models import AsyncReport


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
            if data.get('source') == 'HT':
                params = data.get('input_params')
                # data['input_params'] = {
                #     'id__in': params.get('id_list'),

                # }
                print(params)
                pass
            else:
                
                pass
        else:
            pass
        if errors:
            raise serializers.ValidationError(errors)
        else:
            return data
    
    class Meta:
        model = AsyncReport
        fields = ('id', 'input_params', 'source',
                  'report_name', 'report_type',
                  'status', 'report', 'user',
                  'emails', 'frequency', 'schedule_time')


class UserMetaModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = get_user_model()
        fields = ('id', 'email', 'first_name', 'last_name')


class AsyncReportListSerializer(serializers.ModelSerializer):
    STATUS = {
        item[0] : item[1]
        for item in AsyncReport.STATUS
    }
    REPORT_TYPE = {
        item[0] : item[1]
        for item in AsyncReport.REPORT_TYPES
    }
    REPORT_CHOICE = {
        item[0] : item[1]
        for item in AsyncReport.REPORT_CHOICES
    }
    emails = serializers.ListField(child=serializers.EmailField(max_length=100,
                                                                allow_blank=False),
                                   allow_empty=True)
    user = UserMetaModelSerializer(read_only=True)
    status = serializers.SerializerMethodField()
    report_type = serializers.SerializerMethodField()
    report_name = serializers.SerializerMethodField()
    
    def get_report_type(self, instance):
        return AsyncReportListSerializer.REPORT_TYPE.get(instance.report_type)
    
    def get_status(self, instance):
        return AsyncReportListSerializer.STATUS.get(instance.status)

    def get_report_name(self, instance):
        return AsyncReportListSerializer.REPORT_CHOICE.get(instance.report_name)
    
    class Meta:
        model = AsyncReport
        fields = ('id', 'rid', 'status',
                  'report_type', 'report_name', 
                  'user', 'report', 'emails')


class AsyncReportRetrieveSerializer(AsyncReportListSerializer):
    
    class Meta:
        model = AsyncReport
        exclude = ('input_params',)