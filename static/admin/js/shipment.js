/* This js is only for PlanShipment and Damage Dashboard Admin. */
(function($) {
    $(document).ready(function() {
    changeReturnedQty()
    changeDamagedQty()
    changeDeliveredQty()
    hideLink()
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

function changeReturnedQty(){
    $(document).ready(function(){
        xx = [0,1,2,3,4,5,6]
        $("input[name$='-returned_qty']").keyup(function(){
    for(var i=0;i<10;i++){
        var sum = 0
        for (var j=0; j<10;j++){
            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-returned_qty` + "]").val())
            if (isNaN(tot)){
                continue
            }
            sum +=tot
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-returned_qty` + "]").val(sum);
        }
        }
        });
    })
}

function changeDamagedQty(){
    $(document).ready(function(){
        xx = [0,1,2,3,4,5,6]
        $("input[name$='-damaged_qty']").keyup(function(){
    for(var i=0;i<10;i++){
        var sum = 0
        for (var j=0; j<10;j++){
            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-damaged_qty` + "]").val())
            if (isNaN(tot)){
                continue
            }
            sum +=tot
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-damaged_qty` + "]").val(sum);
        }
        }
        });
    })
}

function changeDeliveredQty(){
    $(document).ready(function(){
        xx = [0,1,2,3,4,5,6]
        $("input[name$='-delivered_qty']").keyup(function(){
    for(var i=0;i<10;i++){
        var sum = 0
        for (var j=0; j<10;j++){
            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-delivered_qty` + "]").val())
            if (isNaN(tot)){
                continue
            }
            sum +=tot
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-delivered_qty` + "]").val(sum);
        }
        }
        });
    })
}

function hideLink(){
    $(document).ready(function(){
        $(".djn-add-item").hide()
    })
}