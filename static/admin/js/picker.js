/* This js is only for Order, Invoice and Picker Dashboard Admin. */
(function($) {
    $(document).ready(function() {
      $("#changelist-form").submit(function( event ) {
        event.preventDefault()
            var shipment_id = [];
            $.each($("input[name='_selected_action']:checked"), function(){
                shipment_id.push($(this).val());
            });
            if(shipment_id.length < 1)
            {
            alert("No Order has been selected. Please select atleast one order to perform action.");
            }
            else
            {
            event.currentTarget.submit();
            }
    });
  });
})(django.jQuery);