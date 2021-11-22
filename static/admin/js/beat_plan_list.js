/* This js is used for BeatPlanningAdmin. */
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
            alert("No data selected, please select atleast one row to perform action.");
            }
            else
            {
            event.currentTarget.submit();
            }
    });
  });
})(django.jQuery);