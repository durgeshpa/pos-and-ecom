(function ($) {
   $(document).ready(function() {
        var row = 0
        var dt = ""
        var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
        $.ajax({ data: ({'order_no':$('#id_order_no').val()}) ,
                type: 'GET',
                dataType: 'json',
                url: host+'retailer/sp/retailer-cart/',
                success: function(response) {
                     if(response['is_success']) {
                        $("#loading").hide();
                        $.each(response['response_data']['rt_cart_list'], function(key, val) {
                            row = (key % 2)+1
                            $("#data").append("<tr class='row"+row+"'><td>"+val.cart_product.product_name+"</td><td>"+val.cart_product_price.mrp+"</td><td>"+val.product_price+"</td><td>"+val.qty+"</td><td>"+val.no_of_pieces+"</td></tr>")
                        });

                     }
                },
                error: function (request, status, error) {
                     console.log(request.responseText);
                }
            });

    });

})(django.jQuery);