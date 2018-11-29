(function ($) {
    $(document).on("submit", "form", function (e) {
    var oForm = $(this);
    var formId = oForm.attr("id");
    if( $("#id_brand").val() &&  $("#id_supplier_state").val() && $("#id_supplier_name").val() &&
     $("#id_gf_shipping_address").val() && $("#id_gf_billing_address").val() &&  $("#id_po_validity_date").val() && $("#id_cart_list-0-cart_product").val() ){
        var firstValue = oForm.find("input").first().val();
        var c = confirm("Are you want to sure ?");
        return c;
     }
})
})(django.jQuery);
