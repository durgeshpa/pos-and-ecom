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

(function($) {
$(document).ready(function(){
       //$('.return_table_inline').find('input').prop("readonly", true)
       $('.return_batch_inline table tr.has_original').each(function(){
            var delivered_qty=0
            delivered_qty = $(this).find("input[name$='-quantity']").val()-$(this).find("input[name$='-returned_qty']").val()-
            $(this).find("input[name$='-returned_damage_qty']").val()
            $(this).find("input[name$='-delivered_qty']").val(delivered_qty)

       })
       $('.return_batch_inline').find('input').prop("readonly", false)
       $("input[name$='-delivered_qty']").prop("readonly", true)
       $("input[name$='-shipped_qty']").prop("readonly", true)
       $("input[name$='-quantity']").prop("readonly", true)
    })
})(django.jQuery);

(function($) {
$(document).ready(function(){
       $("input").change(function(){
       if($(this).val()<0)
       {
            $(this).val(0)
       }
//       for(var i=0;i<10;i++){
//        var sum = 0
//           for (var j=0; j<10;j++){
//                var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-returned_qty` + "]").val())
//                if (isNaN(tot)){
//                    continue
//                }
//                sum +=tot
//                $("input[name=" + `rt_order_product_order_product_mapping-${i}-returned_qty` + "]").val(sum);
//                }
//           }
//        for(var i=0;i<10;i++){
//        var sum = 0
//        for (var j=0; j<10;j++){
//            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-returned_damage_qty` + "]").val())
//            if (isNaN(tot)){
//                continue
//            }
//            sum +=tot
//            $("input[name=" + `rt_order_product_order_product_mapping-${i}-returned_damage_qty` + "]").val(sum);
//        }
//        }
        $('table tr.has_original').each(function(){
            var delivered_qty=0
            delivered_qty = $(this).find("input[name$='-quantity']").val()-$(this).find("input[name$='-returned_qty']").val()-
            $(this).find("input[name$='-returned_damage_qty']").val()
            if (isNaN(delivered_qty))
            {
                delivered_qty = $(this).find("input[name$='-shipped_qty']").val()-$(this).find("input[name$='-returned_qty']").val()-
                $(this).find("input[name$='-returned_damage_qty']").val()
            }
            $(this).find("input[name$='-delivered_qty']").val(delivered_qty)

       })
    })


    })
})(django.jQuery);

function changeReturnedQty(){
//    $(document).ready(function(){
//        xx = [0,1,2,3,4,5,6]
//        $("input[name$='-returned_qty']").keyup(function(){
//    for(var i=0;i<10;i++){
//        var sum = 0
//        for (var j=0; j<10;j++){
//            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-returned_qty` + "]").val())
//            if (isNaN(tot)){
//                continue
//            }
//            sum +=tot
//            $("input[name=" + `rt_order_product_order_product_mapping-${i}-returned_qty` + "]").val(sum);
//        }
//        }
//        });
//    })
}

function changeDamagedQty(){
//    $(document).ready(function(){
//        xx = [0,1,2,3,4,5,6]
//        $("input[name$='-returned_damage_qty']").keyup(function(){
//    for(var i=0;i<10;i++){
//        var sum = 0
//        for (var j=0; j<10;j++){
//            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-returned_damage_qty` + "]").val())
//            if (isNaN(tot)){
//                continue
//            }
//            sum +=tot
//            $("input[name=" + `rt_order_product_order_product_mapping-${i}-returned_damage_qty` + "]").val(sum);
//        }
//        }
//        });
//    })
}


function changeDeliveredQty(){
//    $(document).ready(function(){
//        xx = [0,1,2,3,4,5,6]
//        $("input[name$='-delivered_qty']").keyup(function(){
//    for(var i=0;i<10;i++){
//        var sum = 0
//        for (var j=0; j<10;j++){
//            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-delivered_qty` + "]").val())
//            if (isNaN(tot)){
//                continue
//            }
//            sum +=tot
//            $("input[name=" + `rt_order_product_order_product_mapping-${i}-delivered_qty` + "]").val(sum);
//        }
//        }
//        });
//    })
}

function hideLink(){
    $(document).ready(function(){
        $(".djn-add-item").hide()
    })
}