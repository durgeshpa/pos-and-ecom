/*
(function($) {
    $(document).ready(function() {
     var selectField = $('#id_audit_type'),
            verified = $('.abcdefg');


*/
/*
         var element = document.getElementsByClassName("form-row field-audit_inventory_type");
         var i;
         for (i = 0; i < element.length; i++) {
            element[i].style ="display: none!important";
         }

         var element = document.getElementsByClassName("form-row field-audit_level");
         var i;
         for (i = 0; i < element.length; i++) {
            element[i].style ="display: none!important";
         }

         var element = document.getElementsByClassName("form-row field-auditor");
         var i;
         for (i = 0; i < element.length; i++) {
            element[i].style ="display: none!important";
         }
         *//*



      $("#id_audit_type").change(function( event ) {
         var selected = $(this).val();
         if(selected == 0){
             var elementDate = document.getElementsByClassName("form-row field-audit_level");
             var i;
             for (i = 0; i < elementDate.length; i++) {
                elementDate[i].style ="display: block!important";
             }

             var elementDate = document.getElementsByClassName("form-row field-auditor");
             var i;
             for (i = 0; i < elementDate.length; i++) {
                elementDate[i].style ="display: block!important";
             }

             var elementDate = document.getElementsByClassName("form-row field-audit_inventory_type");
             var i;
             for (i = 0; i < elementDate.length; i++) {
                elementDate[i].style ="display: none!important";
             }
         }else if(selected == 2){
             var elementDate = document.getElementsByClassName("form-row field-audit_inventory_type");
             var i;
             for (i = 0; i < elementDate.length; i++) {
                elementDate[i].style ="display: block!important";
             }

             var elementDate = document.getElementsByClassName("form-row field-auditor");
             var i;
             for (i = 0; i < elementDate.length; i++) {
                elementDate[i].style ="display: none!important";
             }

             var elementDate = document.getElementsByClassName("form-row field-audit_level");
             var i;
             for (i = 0; i < elementDate.length; i++) {
                elementDate[i].style ="display: none!important";
             }
         }
    });
  });
})(django.jQuery);*/

(function($) {
    $(function() {
        var manual = $('.manual'),
            automated = $('.automated');

        var bin = $('.field-bin'),
            sku = $('.field-sku');
//
//            manual.hide();
//            automated.hide();
//            bin.hide();
//            sku.hide();

        function toggleAuditType(value) {
            if (value != ''){
                manual.hide();
                automated.hide();
            }else if (value == 0) {
                alert("value is zero");

                manual.show();
                automated.hide();
            } else if(value == 2){
                manual.hide();
                automated.show()
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
        toggleAuditType($('#id_audit_type').val())
        toggleAuditLevel($('#id_audit_level').val())

        $('#id_audit_type').change(function() {
            toggleAuditType($(this).val());
        });

        $('#id_audit_level').change(function() {
            toggleAuditLevel($(this).val());
        });
    });
})(django.jQuery);