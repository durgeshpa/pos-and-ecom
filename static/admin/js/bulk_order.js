(function($) {
    $(document).on('change', '#id_seller_shop', function(index){
    $('.help').find('a').each(function() {
      var seller_shop_id = $('#id_seller_shop').val();
      var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
      var csv = host + 'admin/products/product/cart-products-mapping/'
      $(this).attr('href',csv + seller_shop_id);
    });
    });

    $(document).ready(function() {
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
