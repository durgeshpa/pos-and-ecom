(function ($) {
    function openDetails() {
      alert('changed')
    }

    $(document).on('change', '#id_supplier_name', function(index){
    $('.help').find('a').each(function() {
      var supplier_id = $('#id_supplier_name').val();
      var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
      var csv = host + 'admin/products/product/products-vendor-mapping/'
      $(this).attr('href',csv + supplier_id);
    });
    });

   $(document).on('change', '.select2-hidden-accessible', function(index){
        if ($(this).data("autocomplete-light-url") == '/gram/brand/vendor-product-autocomplete/'){
            var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
            var supplier_id = $('#id_supplier_name').val();
            var present_id = $(this) ;
            $.ajax({ data: ({'supplier_id':supplier_id, 'product_id':$(this).val()}) ,
                type: 'GET',
                dataType: 'json',
                url: host+'gram/brand/vendor-product-price/',
                success: function(response) {
                     var row_id = present_id.closest(".form-row").attr("id");
                     var row_no = row_id.match(/(\d+)/g);
                     if(response['success']) {
                        $('#cart_list-'+row_no+' td.field-tax_percentage p').text(response.tax_percentage);
                        $('#id_cart_list-'+row_no+'-price').val(response.price);
                        $('#id_cart_list-'+row_no+'-case_size').val(response.case_size);
                        $('#id_cart_list-'+row_no+'-inner_case_size').val(response.inner_case_size);
                        $('#cart_list-'+row_no+' td.field-case_sizes p').text(response.case_size);
                        $('#cart_list-'+row_no+' td.field-sku p').text(response.sku);
                        $('#cart_list-'+row_no+' td.field-mrp p').text(response.mrp);

                     }else{
                        $('#cart_list-'+row_no+' td.field-tax_percentage p').text(response.tax_percentage);
                        $('#id_cart_list-'+row_no+'-price').val(0);
                        $('#id_cart_list-'+row_no+'-case_size').val(0);
                        $('#id_cart_list-'+row_no+'-inner_case_size').val(0);
                        $('#cart_list-'+row_no+' td.field-case_sizes p').text("-");
                        $('#cart_list-'+row_no+' td.field-sku p').text("-");
                        $('#cart_list-'+row_no+' td.field-mrp p').text("-");
                     }
                },
                error: function (request, status, error) {
                     console.log(request.responseText);
                }
            });
        }
    });

    $(document).on('input', '.field-no_of_cases input[type=text]', function(index){
        var row_id = $(this).closest(".form-row").attr("id");
        var row_no = row_id.match(/(\d+)/g);
        var sub_total = parseFloat($('#id_cart_list-'+row_no+'-price').val()) * (parseFloat($('#cart_list-'+row_no+' td.field-case_sizes p').text()) * parseFloat($('#id_cart_list-'+row_no+'-no_of_cases').val()))
        $('#cart_list-'+row_no+' td.field-total_no_of_pieces p').text(parseFloat($('#cart_list-'+row_no+' td.field-case_sizes p').text()) * parseFloat($('#id_cart_list-'+row_no+'-no_of_cases').val()));
        $('#cart_list-'+row_no+' td.field-sub_total p').text(sub_total.toFixed(2));
        $('#id_cart_list-'+row_no+'-no_of_pieces').val(parseFloat($(this).val())* parseFloat($('#cart_list-'+row_no+' td.field-case_sizes p').text()));

    });

    $(document).on('input', '.field-price input[type=number]', function(index){
        var row_id = $(this).closest(".form-row").attr("id");
        var row_no = row_id.match(/(\d+)/g);
        var sub_total = parseFloat($('#id_cart_list-'+row_no+'-price').val()) * (parseFloat($('#cart_list-'+row_no+' td.field-case_sizes p').text()) * parseFloat($('#id_cart_list-'+row_no+'-no_of_cases').val()))
        $('#cart_list-'+row_no+' td.field-sub_total p').text(sub_total.toFixed(2));
    });

    $("#id_cart_list-0-case_size,#id_cart_list-0-number_of_cases").keyup(function () {

    $('#id_cart_list-0-total_price').val($('#id_cart_list-0-case_size').val() * $('#id_cart_list-0-number_of_cases').val());

    });

     $(document).on('input', '.vIntegerField', function(index){
         var row_id = $(this).closest(".form-row").attr("id");
         var row_no = row_id.match(/(\d+)/g);
         $('#id_cart_list-'+row_no+'-total_price').val(parseFloat($('#id_cart_list-'+row_no+'-price').val()) * parseFloat($('#id_cart_list-'+row_no+'-inner_case_size').val()) * parseFloat($('#id_cart_list-'+row_no+'-case_size').val()) * parseFloat($(this).val()))
     });

    $(document).ready(function() {
        console.log( "document loaded" );
        $('.field-no_of_pieces input[type="text"]').prop('readonly', true);


        var row = 0
        var dt = ""
        var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
        $.ajax({ data: ({'po':$('#id_cart_list-0-cart').val()}) ,
                type: 'GET',
                dataType: 'json',
                url: host+'admin/gram_to_brand/cart/message-list/',
                success: function(response) {
                    // Po buttons visiblity code
                    if (response['po_status']== 'PDLV') {
                        $(':input[name="_close"]').prop('disabled', false);
                        $(':input[name="_disapprove"]').prop('disabled', true);
                        $(':input[name="_approve"]').prop('disabled', true);
                        $(':input[name="_approval_await"]').prop('disabled', true);
                    }else if(response['po_status']== 'WAIT') {
                        $(':input[name="_disapprove"]').prop('disabled', false);
                        $(':input[name="_approve"]').prop('disabled', false);
                        $(':input[name="_close"]').prop('disabled', true);
                        $(':input[name="_approval_await"]').prop('disabled', true);

                    }else if(response['po_status']== 'OPEN' || response['po_status']== 'WAIT'){
                        $(':input[name="_approval_await"]').prop('disabled', false);
                        $(':input[name="_close"]').prop('disabled', true);
                        $(':input[name="_disapprove"]').prop('disabled', true);
                        $(':input[name="_approve"]').prop('disabled', true);

                    }else{
                        $(':input[name="_close"]').prop('disabled', true);
                        $(':input[name="_disapprove"]').prop('disabled', true);
                        $(':input[name="_approve"]').prop('disabled', true);
                        $(':input[name="_approval_await"]').prop('disabled', true);
                    }

                    $("#loading").hide();
                    if(response['is_success']) {
                        $("#data").append("<tr class='row0'><td>"+response['response_data'][0].user+"</td><td>"+response['response_data'][0].message+"</td><td>"+response['response_data'][0].created_at+"</td></tr>")
                    }
                    else{
                        $("#data").append("<tr class='row0'><td>-</td><td>-</td><td>-</td></tr>")
                    }
                },
                error: function (request, status, error) {
                     console.log(request.responseText);
                }
            });

        $('.submit-row').on('click','input[type=submit]', function(e){
            var c = confirm("Are you sure?");
            return c;
        });
        
        $('.submit-row').on('click','input[name="_disapprove"]', function(e){
            console.log("inside disapprove")
            if ($('textarea[name="message"]').val().trim()=='') {
                alert("Please enter some message");
                event.preventDefault();
            }
        });

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
