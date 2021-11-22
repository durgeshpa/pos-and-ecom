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

    $('.order-po-create').click(function() {
        id_el = $(this);
        order_id = $(this).attr('data-id');
        ajax_url = "/retailer/sp/create-franchise-po/" + order_id + "/"
        $.ajax({
        url: ajax_url,
        type : 'GET',
        data: { 'order_id': order_id },
        contentType: "application/json; charset=utf-8",
        success: function (data) {
            id_el.siblings('.create-po-resp').remove();
            console.log(data);
            id_el.after(data.response);
        },
        error: function (data) {
            console.log("ERROR");
            console.error(data);
            return true;
        },
        cache: false
    });
    });
  });
})(django.jQuery);