(function ($) {
   $(document).on('change', '.select2-hidden-accessible', function(index){
        if ($(this).data("autocomplete-light-url") == '/admin/products/product/product-price-autocomplete/'){
            var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
            var present_id = $(this) ;
            $.ajax({ data: ({'product_id':$(this).val() }) ,
                type: 'GET',
                dataType: 'json',
                url: host+'admin/brand/vendor/search-product/',
                success: function(response) {
                     var row_id = present_id.closest(".form-row").attr("id");
                     var row_no = row_id.match(/(\d+)/g);
                     if(response['success']) {
                        $('#vendor_brand_mapping-'+row_no+' td.field-sku p').text(response['product_sku'])
                     }else{
                        $('#vendor_brand_mapping-'+row_no+' td.field-sku p').text("-");
                     }
                },
                error: function (request, status, error) {
                     console.log(request.responseText);
                }
            });
        }
    });

})(django.jQuery);
