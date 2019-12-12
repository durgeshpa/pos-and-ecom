/*(function($) {
     $(document).ready(function() {
        
        if ($("#id_payment_mode_name option:selected").val() == "cash_payment")
        {

            ("#id_reference_no").hide();
        }

        else
            ("#id_reference_no").show();   
    });
 })(django.jQuery);

*/
(function($) {
    $(function() {
        var selectField = $('#id_payment_mode_name'),
            verified = $('#id_reference_no');
            verified1 = $('#id_online_payment_type');
            //verified2 = $('#id_online_payment_type, #id_reference_no');
        function toggleVerified(value) {
            if (value != "cash_payment"){
                verified.show();
                verified1.show();
                verified.attr('required', true);  
                verified1.attr('required', true);  
            }
            else
            {
                verified.hide();
                verified1.hide();
                verified.removeAttr('required');
                verified.removeAttr('required');
            }

            //value != 'cash_payment' ? verified.show() : verified.hide();
        }
        //        alert("helo world");
        // show/hide on load based on pervious value of selectField
        toggleVerified(selectField.val());

        // show/hide on change
        selectField.change(function() {
            toggleVerified($(this).val());
        });
    });
})(django.jQuery);