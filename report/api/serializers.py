# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from rest_framework import serializers

from report.models import ReportChoice, ReportRequest, ScheduledReport
from report.validators import validate_input_params


class ReportModelSerializer(serializers.ModelSerializer):
    
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
                    frequency = data.get('frequency')
                    if frequency == "Daily":
                        start = datetime.now() - timedelta(days=1)
                    elif frequency in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
                        start = datetime.now() - timedelta(days=7)
                    else:
                        start = datetime.now() - timedelta(days=30)
                    data['input_params']['date_start'] = start.strftime("%Y-%m-%d")
            else:
                pass
            report_choice = data.get('report_choice')
            input_params_errors = validate_input_params(data.get('input_params'), report_choice.required_mappings)
            if input_params_errors:
                errors['input_params'] = input_params_errors
            # if data.get('source', 'HT') == 'HT':
            #     errors = validate_host_input_params(data.get('report_name'), 
            #                                         data.get('input_params'), 
            #                                         errors,
            #                                         data.get('report_type'))
            #     if errors:
            #         raise serializers.ValidationError(errors)
            #     else:
            #         data['input_params'] = set_host_input_params(data.get('report_name'), 
            #                                                      data.get('input_params'), 
            #                                                      data.get('report_type'), 
            #                                                      data.get('frequency'))
            #         return data
            # else:
            #     errors = validate_redash_input_params(data.get('report_name'), 
            #                                           data.get('input_params'), 
            #                                           errors, 
            #                                           data.get('report_type'))
            #     if errors:
            #         raise serializers.ValidationError(errors)
            #     else:
            #         data['input_params'] = set_redash_input_params(data.get('report_name'), 
            #                                                        data.get('input_params'))
            #         return data
        else:
            pass
        if errors:
            raise serializers.ValidationError(errors)
        return data
    
    class Meta:
        model = ReportRequest
        fields = ('id', 'input_params', 'report_choice',
                  'report_type', 'status', 'report', 'user',
                  'emails', 'frequency', 'schedule_time')


class UserMetaModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = get_user_model()
        fields = ('id', 'email', 'first_name', 'last_name', 'phone_number')


class ScheduledReportMetaSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ScheduledReport
        fields = ('id', 'report', 'created_at')


class ReportChoiceMetaSerializer(serializers.ModelSerializer):
    MODEL_CHOICES = {
        item[0] : item[1]
        for item in ReportChoice.REPORT_CHOICES
    }
    target_model = serializers.SerializerMethodField()
    
    def get_target_model(self, instance):
        return ReportChoiceMetaSerializer.MODEL_CHOICES.get(instance.target_model)
    
    class Meta:
        model = ReportChoice
        fields = ('id', 'name', 'target_model', 'created_at')


class ReportListSerializer(serializers.ModelSerializer):
    STATUS = {
        item[0] : item[1]
        for item in ReportRequest.STATUS
    }
    REPORT_TYPE = {
        item[0] : item[1]
        for item in ReportRequest.REPORT_TYPES
    }
    emails = serializers.ListField(child=serializers.EmailField(max_length=100,
                                                                allow_blank=False),
                                   allow_empty=True)
    user = UserMetaModelSerializer(read_only=True)
    status = serializers.SerializerMethodField()
    report_type = serializers.SerializerMethodField()
    scheduled_reports = serializers.SerializerMethodField()
    report_choice = ReportChoiceMetaSerializer(read_only=True)
    
    def get_report_type(self, instance):
        return ReportListSerializer.REPORT_TYPE.get(instance.report_type)
    
    def get_status(self, instance):
        return ReportListSerializer.STATUS.get(instance.status)
    
    def get_scheduled_reports(self, instance):
        if instance.report_type == 'SC':
            return ScheduledReportMetaSerializer(instance.reports.all(), many=True).data
        else:
            return None
    
    class Meta:
        model = ReportRequest
        fields = ('id', 'rid', 'status',
                  'report_type', 'report_choice', 
                  'user', 'report', 'emails', 'scheduled_reports')


class ReportRetrieveSerializer(ReportListSerializer):
    
    class Meta:
        model = ReportRequest
        exclude = ('input_params',)