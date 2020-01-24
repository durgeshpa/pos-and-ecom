(function($) {
    $(document).on('change', '#id_seller_shop', function(index){
    $('.help').find('a').each(function() {
      var seller_shop_id = $('#id_seller_shop').val();
      var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
      var csv = host + 'admin/products/product/cart-products-mapping/'
      $(this).attr('href',csv + seller_shop_id);
    });
    });

})(django.jQuery);
