from rest_framework import serializers

from audit.models import AuditDetail, AUDIT_LEVEL_CHOICES, AUDIT_DETAIL_STATE_CHOICES


class AuditDetailSerializer(serializers.ModelSerializer):
    audit_no = serializers.SerializerMethodField('m_audit_no')
    audit_level = serializers.SerializerMethodField('m_audit_level')
    audit_state = serializers.SerializerMethodField('m_audit_state')

    def m_audit_no(self, obj):
        return obj.id

    def m_audit_level(self, obj):
        return AUDIT_LEVEL_CHOICES[obj.audit_level]

    def m_audit_state(self, obj):
        return AUDIT_DETAIL_STATE_CHOICES[obj.state]

    class Meta:
        model = AuditDetail
        fields = ('audit_no', 'audit_level', 'audit_state', 'created_at')
