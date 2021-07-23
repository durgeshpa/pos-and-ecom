(function($) {
  $(document).ready(function() {
    getProductDetails()
});
})(django.jQuery);

function getProductDetails() {
    if (!$) {
        $ = django.jQuery;
    }
    val = document.getElementById("id_product_ref").value;
    ajax_url = "/pos/fetch-retailer-product/";
    $.ajax({
        url: ajax_url,
        type : 'GET',
        data: { 'product': val },
        contentType: "application/json; charset=utf-8",
        success: function (data) {
            if(data.found === true){
                document.getElementById('id_mrp').value = data.mrp;
                document.getElementById('id_selling_price').value = data.selling_price;
                document.getElementById('id_product_ean_code').value = data.product_ean_code;
            }
            return true;
        },
        error: function (data) {
            console.log("ERROR");
            console.error(data);
            return true;
        },
        cache: false
    });
}