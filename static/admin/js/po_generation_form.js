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
   $(document).on('change', '.select2-hidden-accessible', function(index){
        if ($(this).data("autocomplete-light-url") == '/gram/brand/vendor-product-autocomplete/'){
            var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
            var supplier_id = $('#id_supplier_name').val();
            var present_id = $(this) ;
            $.ajax({ data: ({'supplier_id':supplier_id, 'product_id':$(this).val() }) ,
                type: 'GET',
                dataType: 'json',
                url: host+'gram/brand/vendor-product-price/',
                success: function(response) {
                     var row_id = present_id.closest(".form-row").attr("id");
                     var row_no = row_id.match(/(\d+)/g);
                     if(response['success']) {
                        $('#id_cart_list-'+row_no+'-price').val(response.price);
                        $('#id_cart_list-'+row_no+'-case_size').val(response.case_size);
                     }else{
                        $('#id_cart_list-'+row_no+'-price').val(0);
                        $('#id_cart_list-'+row_no+'-case_size').val(0);
                     }
                },
                error: function (request, status, error) {
                     console.log(request.responseText);
                }
            });
        }
    });

    $("#id_cart_list-0-case_size,#id_cart_list-0-number_of_cases").keyup(function () {

    $('#id_cart_list-0-total_price').val($('#id_cart_list-0-case_size').val() * $('#id_cart_list-0-number_of_cases').val());

    });

   // function calculate() {
  	// 	var case_size = document.getElementById('id_cart_list-0-case_size').value;
  	// 	var number_of_cases = document.getElementById('id_cart_list-0-number_of_cases').value;
   //    var price = document.getElementById('id_cart_list-0-price').value;
  	// 	var total_price = document.getElementById('id_cart_list-0-total_price');
  	// 	var multiply = myBox1 * myBox2 * myBox3;
  	// 	result.value = multiply;


  	//}





})(django.jQuery);
