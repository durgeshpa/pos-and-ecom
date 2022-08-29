(function($) {
  $(document).ready(function() {

    flatpickr("input[id$='rescheduling_date']", {
    dateFormat: "Y-m-d",
    minDate: new Date().fp_incr(1), // tommorow
    maxDate: new Date().fp_incr(3) // 3 days from now
  });
});
})(django.jQuery);

(function($) {
  $(document).ready(function() {
    shipment_status = ['OUT_FOR_DELIVERY','PARTIALLY_DELIVERED_AND_COMPLETED',
    'FULLY_RETURNED_AND_COMPLETED','FULLY_DELIVERED_AND_COMPLETED','RESCHEDULED']
    if ($.inArray($('select#id_shipment_status').val(), shipment_status) == -1){
           $("select[id$='rescheduling_reason']").css('pointer-events','none');
           $("input[id$='rescheduling_date']").css('pointer-events','none');
    }
    if ($('select#id_shipment_status').val() == "RESCHEDULED"){
            $("select[id$='rescheduling_reason']").css('pointer-events','none');
    }
});
})(django.jQuery);

