/* This js is only for Order, Invoice and Picker Dashboard Admin. */
(function($) {
    $(document).ready(function() {
      $("#changelist-form").submit(function( event ) {
        event.preventDefault()
        var e = document.getElementsByName("action")[0];
        var action_value = e.options[e.selectedIndex].value;

            var shipment_id = [];
            $.each($("input[name='_selected_action']:checked"), function(){
                shipment_id.push($(this).val());
            });
            if(shipment_id.length < 1)
            {
            alert("No Order has been selected. Please select atleast one order to perform action.");
            }if((document.title.indexOf("GRN") !== -1)&&(shipment_id.length >1)&&(action_value=="download_barcode")){
             alert("More than 1 GRN selected. 1 GRN is allowed at a time for Barcode Download")
            }
            else
            {
            event.currentTarget.submit();
            }
    });
  });
})(django.jQuery);