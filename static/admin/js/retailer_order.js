(function ($) {
   $(document).ready(function() {
        var row = 0
        var dt = ""
        var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
        $.ajax({ data: ({'order_no':$('#id_order_no').val()}) ,
                type: 'GET',
                dataType: 'json',
                url: host+'retailer/sp/order-list/',
                success: function(response) {
                     if(response['is_success']) {
                        $("#loading").hide();
                        $.each(response['response_data'], function(key, val) {
                            $('#'+val.id+'-seller_shop').text(val.seller_shop)
                            $('#'+val.id+'-buyer_shop').text(val.buyer_shop)
                            $('#'+val.id+'-order_status').text(val.order_status)

                            $('#'+val.id+'-payment_mode').text(val.payment_mode)
                            $('#'+val.id+'-invoice_no').html(val.invoice_no)
                            $('#'+val.id+'-shipment_created_date').html(val.shipment_created_date)
                            $('#'+val.id+'-invoice_amount').html(val.invoice_amount)
                            $('#'+val.id+'-shipment_status').html(val.shipment_status)
                            $('#'+val.id+'-delivery_date').html(val.delivery_date)
                            $('#'+val.id+'-cn_amount').html(val.cn_amount)
                            $('#'+val.id+'-cash_collected').html(val.cash_collected)
                            $('#'+val.id+'-damaged_amount').html(val.damaged_amount)
                            $('#'+val.id+'-delivered_amount').html(val.delivered_amount)
                        });

                     }
                },
                error: function (request, status, error) {
                     console.log(request.responseText);
                }
            });

    });

})(django.jQuery);
