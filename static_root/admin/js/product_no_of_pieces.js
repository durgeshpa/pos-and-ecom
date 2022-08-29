
(function($) {
    'use strict';
    $(document).ready(function() {
        Select2Field('#id_seller_shop');
        Select2Field('#id_buyer_shop');
        Select2Field('#id_cart_status');

        //$("[id$='no_of_pieces']").prop('readonly', true);

        OnChangeQty();
        OnChangeProduct();
    });

    function OnChangeProduct(){
        var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';


        $("[id$='cart_product']").change(function() {
            var row_id = $(this).closest(".form-row").attr("id");
            var row_no = row_id.match(/(\d+)/g);
            var product_id = '#id_rt_cart_list-'+row_no+'-cart_product option:selected';
            var no_of_pieces_id = '#id_rt_cart_list-'+row_no+'-no_of_pieces';
            var selected_product = $(product_id).val();

                $.ajax({ data: ({'cart_product_id':selected_product }) ,
                    type: 'GET',
                    dataType: 'json',
                    url: host+'admin/retailer_to_sp/cart/get-pcs-from-qty/',
                    success: function(response) {

                         if(response['success']) {
                            var response_case_size = response['case_size'];
                            var response_inner_case_size = response['inner_case_size']

                            $("#id_rt_cart_list-"+row_no+"-product_case_size").val(response_case_size);
                            $("#id_rt_cart_list-"+row_no+"-product_inner_case_size").val(response_inner_case_size);

                            var qty = $("#id_rt_cart_list-"+row_no+"-qty").val();
                            $(no_of_pieces_id).val(qty*response_inner_case_size);

                         }else{
                            $("[id$='no_of_pieces']").prop('readonly', false);
                            alert('Unable to fetch no. of pieces for '+$(product_id).text());
                         }

                    },
                    error: function (request, status, error) {
                         console.log(request.responseText);
                    }
                });
        });
    }

    function OnChangeQty(){
        $("[id$='qty']").on("change paste keyup", function() {
            var row_id = $(this).closest(".form-row").attr("id");
            var row_no = row_id.match(/(\d+)/g);
            var no_of_pieces_id = '#id_rt_cart_list-'+row_no+'-no_of_pieces';
            var qty = $(this).val();
            var case_size = $("#id_rt_cart_list-"+row_no+"-product_case_size").val();
            var inner_case_size = $("#id_rt_cart_list-"+row_no+"-product_inner_case_size").val();

            $(no_of_pieces_id).val(qty*inner_case_size);
        });
    }

    function Select2Field(id){
        $(id).select2();
    }
})(django.jQuery);
