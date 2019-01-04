(function ($) {
    $(document).on("submit", "form", function (e) {
        var oForm = $(this);
        var formId = oForm.attr("id");
        if( $("#id_state").val() &&  $("#id_gram_factory").val() && $("#id_po_validity_date").val() &&
         $("#id_sp_cart_list-0-cart_product").val() && $("#id_sp_cart_list-0-case_size").val() &&  $("#sp_cart_list-0-number_of_cases").val() && $("#sp_cart_list-0-price").val() ){
            var c = confirm("Are you sure?");
            return c;
         }
    });

   $(document).on('change', '.select2-hidden-accessible', function(index){
        if ($(this).data("autocomplete-light-url") == '/service-partner/gf-product-autocomplete/'){
            var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
            var gf_id = $('#id_gram_factory').val();
            var present_id = $(this) ;

            $.ajax({ data: ({'gf_id':gf_id, 'product_id':$(this).val() }) ,
                type: 'GET',
                dataType: 'json',
                url: host+'service-partner/sp-product-price/',
                success: function(response) {
                     var row_id = present_id.closest(".form-row").attr("id");
                     var row_no = row_id.match(/(\d+)/g);
                     if(response['success']) {
                        $('#id_sp_cart_list-'+row_no+'-case_size').val(response.product_case_size);
                        $('#id_sp_cart_list-'+row_no+'-price').val(response.service_partner_price);
                     }else{
                        $('#id_sp_cart_list-'+row_no+'-case_size').val(0);
                        $('#id_sp_cart_list-'+row_no+'-price').val(0);
                     }
                },
                error: function (request, status, error) {
                     console.log(request.responseText);
                }
            });
        }
    });

//    $("#id_cart_list-0-case_size,#id_cart_list-0-number_of_cases").keyup(function () {
//        $('#id_cart_list-0-total_price').val($('#id_cart_list-0-case_size').val() * $('#id_cart_list-0-number_of_cases').val());
//
//    });

    $(document).on('input', '.vIntegerField', function(index){
        var row_id = $(this).closest(".form-row").attr("id");
        var row_no = row_id.match(/(\d+)/g);
        $('#id_sp_cart_list-'+row_no+'-total_price').val(parseFloat($('#id_sp_cart_list-'+row_no+'-price').val()) * parseFloat($(this).val()))
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
