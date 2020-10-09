function getDefaultChildDetails() {
    val = document.getElementById("id_parent_product").value;
    ajax_url = "/product/fetch-default-child-details/";
    $.ajax({
        url: ajax_url,
        type : 'GET',
        data: { 'parent': val },
        contentType: "application/json; charset=utf-8",
        success: function (data) {
            if(data.found === true){
                document.getElementById('id_product_name').value = data.product_name;
                document.getElementById('id_product_ean_code').value = data.product_ean_code;
                document.getElementById('id_product_mrp').value = data.product_mrp;
                document.getElementById('id_weight_value').value = data.weight_value;
                $('select[id=id_weight_unit]').find('option').remove();
                $('select[id=id_weight_unit]').append($('<option value="'+data.weight_unit.option+'">'+data.weight_unit.text+'</option>'));
                if(!data.enable_use_parent_image_check) {
                    document.getElementById('id_use_parent_image').disabled = true;
                    $("label[for='id_use_parent_image']").text("Use parent image (Parent Image Not Available)");
                    document.getElementById('id_child_product_image').required = true;
                }
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

function getProductDetails() {
    if (!$) {
        $ = django.jQuery;
    }
    val = document.getElementById("id_product").value;
    ajax_url = "/product/fetch-product-details/";
    $.ajax({
        url: ajax_url,
        type : 'GET',
        data: { 'product': val },
        contentType: "application/json; charset=utf-8",
        success: function (data) {
            if(data.found === true){
                document.getElementById('id_mrp').value = data.product_mrp;
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
