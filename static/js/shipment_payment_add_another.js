window.addEventListener("load", function() {
    (function($) {
        var pathname = window.location.pathname;
        var arr = pathname.split('/');
        object_id = arr[arr.length-3]
        user_id = 10//$("#id_user_id").val();
        $("a[id^=add_id_shipment_payment-]").attr("href", "/admin/payments/orderpayment/add/?_to_field=id&_popup=1&user_id="+ user_id +"&object_id=" + object_id);
    })(django.jQuery);
});