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
                console.log(response);
                opt = 0;
                for (index = 0; index < response.product_qty.length; index++) {
                   opt++;

                  //$('#id_grn_order_grn_order_product-'+index+'-product option:eq('+opt+')').prop('selected', true).prop('readonly', true);
                  $('#id_grn_order_grn_order_product-'+index+'-po_product_quantity').val(response.product_qty[index]).prop('readonly', true);
                  $('#id_grn_order_grn_order_product-'+index+'-po_product_price').val(response.product_price[index]).prop('readonly', true);
                  //$('#id_grn_order_grn_order_product-'+index+'-already_grned_product').val(response.product_count[index]);

                }
                //$('#id_grn_order_grn_order_product-0-already_grned_product').val(response.agq).prop('readonly', true);


              },
              error: function (request, status, error) {
                   console.log(request.responseText);
              }
          });
      }
  });



  // $(document).on('change', '.select2-hidden-accessible', function(index){
  //     if ($(this).data("autocomplete-light-url") == '/gram/brand/order-autocomplete/'){
  //         var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
  //         //var order_id = $('#id_order').val();
  //         var present_id = $(this) ;
  //         $.ajax({ data: ({'order_id':$(this).val() }) ,
  //             type: 'GET',
  //             dataType: 'json',
  //             url: host+'gram/brand/po-grned1/',
  //             success: function(response) {
  //               console.log(response);
  //               for (index = 0; index < response.length; index++) {
  //                 $('#id_grn_order_grn_order_product-'+index+'-po_product_quantity').val(response['data']);
  //                 $('#id_grn_order_grn_order_product-'+index+'-po_product_quantity').val(response['data']);
  //
  //               }
  //                 // var row_id = present_id.closest(".form-row").attr("id");
  //                  //var row_no = row_id.match(/(\d+)/g);
  //
  //             },
  //             error: function (request, status, error) {
  //                  console.log(request.responseText);
  //             }
  //         });
  //     }
  // });

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
                      $('#id_grn_order_grn_order_product-'+row_no+'-po_product_quantity').val(response['response_data']).prop('readonly', true);
                   }else{
                      $('#id_grn_order_grn_order_product-'+row_no+'-po_product_quantity').val(0).prop('readonly', true);
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
                        $('#id_grn_order_grn_order_product-'+row_no+'-po_product_price').val(response['response_data']).prop('readonly', true);
                     }else{
                        $('#id_grn_order_grn_order_product-'+row_no+'-po_product_price').val(0).prop('readonly', true);
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
           $.ajax({ data: ({'order_id':order_id, 'product_id':$(this).val() }) ,
               type: 'GET',
               dataType: 'json',
               url: host+'gram/brand/po-grned/',
               success: function(response) {

                    var row_id = present_id.closest(".form-row").attr("id");
                    var row_no = row_id.match(/(\d+)/g);
                    if(response['success']) {
                       $('#id_grn_order_grn_order_product-'+row_no+'-already_grned_product').val(response['response_data']).prop('readonly', true);
                       $('#id_grn_order_grn_order_product-'+row_no+'-already_returned_product').val(response['response_data']).prop('readonly', true)

                    }else{
                       $('#id_grn_order_grn_order_product-'+row_no+'-already_grned_product').val(0).prop('readonly', true);
                       $('#id_grn_order_grn_order_product-'+row_no+'-already_returned_product').val(response['response_data']).prop('readonly', true)
                    }
               },
               error: function (request, status, error) {
                    console.log(request.responseText);
               }
           });
       }
   });

})(django.jQuery);
