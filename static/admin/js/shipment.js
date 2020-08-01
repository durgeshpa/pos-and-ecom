/* This js is only for PlanShipment and Damage Dashboard Admin. */
(function($) {
    $(document).ready(function() {
      $("#changelist-form").submit(function( event ) {
        event.preventDefault()
            var shipment_id = [];
            $.each($("input[name='_selected_action']:checked"), function(){
                shipment_id.push($(this).val());
            });
        ajax_url = "/retailer/sp/shipment_status/"
        $.ajax({
            url: ajax_url,
            type : 'GET',
            data : {
                    'shipment_id' : shipment_id
            },
            success: function (data) {
                data = $.parseJSON(data);
                if(data.count > 1)
                {
                alert(data.count + " files are not downloaded due to QC Pending status.");
                event.currentTarget.submit();
                }
                else if (data.count == 1)
                {
                alert(data.count + " file is not downloaded due to QC Pending status.");
                event.currentTarget.submit();
                }
                else if (data.count == -1)
                {
                alert("No Order has been selected. Please select atleast one order to perform action.");
                }
                else
                {
                event.currentTarget.submit();
                }
            }
         });
    });
  });
})(django.jQuery);
