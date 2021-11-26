(function($) {
  $(document).ready(function() {
    shipment_status = ['OUT_FOR_DELIVERY','PARTIALLY_DELIVERED_AND_COMPLETED',
    'FULLY_RETURNED_AND_COMPLETED','FULLY_DELIVERED_AND_COMPLETED']
    if ($.inArray($('select#id_shipment_status').val(), shipment_status) == -1){
          $("select[id$='not_attempt_reason']").css('pointer-events','none');
     }
});
})(django.jQuery);
