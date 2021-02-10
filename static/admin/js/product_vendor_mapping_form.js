
function getProductMRP(product_id_select) {

    if (!$) {
        $ = django.jQuery;
    }
    var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
    var product_id = product_id_select.value;
    $.ajax({ data: ({'product': product_id}),
        type: 'GET',
        dataType: 'json',
        url: host+'product/fetch-product-details/',
        success: function(response) {
            if(response['found']) {
                $('#id_product_mrp').val(response['product_mrp']);
            }else{
                alert(response)
            }
        }
    });
}