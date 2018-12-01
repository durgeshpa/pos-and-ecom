(function ($) {
  $(document).on('change', '.select2-hidden-accessible', function(index){
      if ($(this).data("autocomplete-light-url") == '/gram/brand/order-autocomplete/'){
          var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
          //var order_id = $('#id_order').val();
          var present_id = $(this) ;
          $.ajax({ data: ({'order_id':$(this).val() }) ,
              type: 'GET',
              dataType: 'json',
              url: host+'gram/brand/po-product/',
              success: function(response) {
                   var row_id = present_id.closest(".form-row").attr("id");
                   var row_no = row_id.match(/(\d+)/g);

                   if(response['success']) {
                      $('#id_grn_order_grn_order_product-'+row_no+'-product').val(response['response_data']);
                      $('#id_grn_order_grn_order_product-'+row_no+'-po_product_quantity').val(response['response_data']);
                      $('#id_grn_order_grn_order_product-'+row_no+'-po_product_price').val(response['response_data']);
                   }else{
                      $('#id_grn_order_grn_order_product-'+row_no+'-product').val(0);
                      $('#id_grn_order_grn_order_product-'+row_no+'-po_product_quantity').val(0);
                      $('#id_grn_order_grn_order_product-'+row_no+'-po_product_price').val(0);
                   }

              },
              error: function (request, status, error) {
                   console.log(request.responseText);
              }
          });
      }
  });



  $(document).on('change', '.select2-hidden-accessible', function(index){
      if ($(this).data("autocomplete-light-url") == '/gram/brand/product-autocomplete/'){
          var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
          var order_id = $('#id_order').val();
          var present_id = $(this) ;
          $.ajax({ data: ({'order_id':order_id, 'cart_product_id':$(this).val() }) ,
              type: 'GET',
              dataType: 'json',
              url: host+'gram/brand/po-product-quantity/',
              success: function(response) {
                   var row_id = present_id.closest(".form-row").attr("id");
                   var row_no = row_id.match(/(\d+)/g);
                   if(response['success']) {
                      $('#id_grn_order_grn_order_product-'+row_no+'-po_product_quantity').val(response['response_data']).prop('disabled', true);
                   }else{
                      $('#id_grn_order_grn_order_product-'+row_no+'-po_product_quantity').val(0).prop('disabled', true);
                   }
              },
              error: function (request, status, error) {
                   console.log(request.responseText);
              }
          });
      }
  });

    $(document).on('change', '.select2-hidden-accessible', function(index){
        if ($(this).data("autocomplete-light-url") == '/gram/brand/product-autocomplete/'){
            var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
            var order_id = $('#id_order').val();
            var present_id = $(this) ;
            $.ajax({ data: ({'order_id':order_id, 'cart_product_id':$(this).val() }) ,
                type: 'GET',
                dataType: 'json',
                url: host+'gram/brand/po-product-price/',
                success: function(response) {
                     var row_id = present_id.closest(".form-row").attr("id");
                     var row_no = row_id.match(/(\d+)/g);
                     if(response['success']) {
                        $('#id_grn_order_grn_order_product-'+row_no+'-po_product_price').val(response['response_data']).prop('disabled', true);
                     }else{
                        $('#id_grn_order_grn_order_product-'+row_no+'-po_product_price').val(0).prop('disabled', true);
                     }
                },
                error: function (request, status, error) {
                     console.log(request.responseText);
                }
            });
        }
   });



})(django.jQuery);
