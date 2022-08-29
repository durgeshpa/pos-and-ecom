
(function($) {
    $(function() {
        var manual = $('.manual'),
            automated = $('.automated');

        var bin = $('.field-bin'),
            sku = $('.field-sku');

        var auditFrom = $('.field-audit_from')

        function toggleAuditType(value) {
            if (value == ''){
                manual.hide();
                automated.hide();
                auditFrom.hide();
            }else if (value == 0) {
                manual.show();
                automated.hide();
            } else if(value == 2){
                manual.hide();
                automated.show()
                auditFrom.hide();
            }
        }
        function toggleAuditLevel(value) {
            if (value == ''){
                sku.hide();
                bin.hide();
            } else if(value == 0) {
                sku.hide();
                bin.show();
            } else if(value == 1){
                sku.show();
                bin.hide();
            }
        }
        toggleAuditType($('#id_audit_run_type').val())
        toggleAuditLevel($('#id_audit_level').val())

        $('#id_audit_run_type').change(function() {
            toggleAuditType($(this).val());
        });

        $('#id_audit_level').change(function() {
            toggleAuditLevel($(this).val());
        });

        $('#id_is_historic').click(function() {
           auditFrom.toggle(this.checked);
        });
    });
})(django.jQuery);