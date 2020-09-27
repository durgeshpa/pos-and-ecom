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

    if ($('select#id_shipment_status').val()!="OUT_FOR_DELIVERY"){
//         $("select[id$='rescheduling_reason']").attr("readonly", true);
//         $("input[id$='rescheduling_date']").attr("readonly", true);
           $("select[id$='rescheduling_reason']").css('pointer-events','none');
           $("input[id$='rescheduling_date']").css('pointer-events','none');

 }
});
})(django.jQuery);

