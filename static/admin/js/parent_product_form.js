jQuery(document).ready(function($){
        var ptr_percent = $('.field-ptr_percent'),
            ptr_type = $('.field-ptr_type');

        var ptr_applicable = $('#id_is_ptr_applicable')
        if($('#id_is_ptr_applicable').is(':checked')){
            ptr_percent.show();
            ptr_type.show();
        }else{
            ptr_percent.hide();
            ptr_type.hide();
        }

        $('#id_is_ptr_applicable').click(function() {
           ptr_percent.toggle(this.checked);
           ptr_type.toggle(this.checked);
        });
    });