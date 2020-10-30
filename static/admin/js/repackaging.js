(function($) {
    $(document).ready(function() {
    var id_available_source_quantity_initial = 0;
    var source_sku_weight = 0;
//    var destination_sku_weight = 0;
    $('#id_source_repackage_quantity').attr('readonly', true);

	$("#id_source_sku").on('change', function(){
	    reset('source');
	    if($(this).val() == ''){
	        return false;
	    }
        $.ajax({ data: ({'sku_id':$(this).val() }) ,
            type: 'GET',
            url: '/admin/products/product/source-repackage-detail/',
            success: function(response) {
                if(response.success){
                    if (response.source_sku_weight == 0 || response.source_sku_weight == ''){
                        alert("Source SKU weight value not found");
                        return false;
                    }
                    $("#id_available_source_quantity").val(response.available_source_quantity);
                    $("#id_available_source_weight").val(response.available_source_quantity * response.source_sku_weight);
                    source_sku_weight = response.source_sku_weight;
                    id_available_source_quantity_initial = response.available_source_quantity;
                } else {
                    alert(response.error)
                }
            },
        });
	});

//	$("#id_destination_sku").on('change', function(){
////	    reset('dest');
////	    if($(this).val() == ''){
////	        return false;
////	    }
////        $.ajax({ data: ({'sku_id':$(this).val() }) ,
////            type: 'GET',
////            url: '/admin/products/product/destination-repackage-detail/',
////            success: function(response) {
////                if(response.success){
////                    if (response.destination_sku_weight == 0 || response.destination_sku_weight == ''){
////                        alert("Destination SKU weight value not found");
////                        return false;
////                    }
////                    $('#id_source_repackage_quantity').attr('readonly', false);
////                    destination_sku_weight = response.destination_sku_weight;
////                } else {
////                    alert(response.error)
////                }
////            },
////        });
//	});

	$("#id_seller_shop").on('change', function(){
        reset('shop');
	});

	$('#id_source_repackage_quantity').on('blur', function(){
	    if($(this).prop('readonly')){
	        return false;
	    }
	    if($(this).val() < 0 || $(this).val() == ''){
	        $(this).val(0);
	    }
	    var repackage_qty = $(this).val();
        set_weights(repackage_qty);
	});

	function reset(type){
	    $("#id_source_repackage_quantity").val(0);
	    $('#id_source_repackage_quantity').attr('readonly', true);
	    if(type == 'shop' || type=='source'){
	        $("#id_available_source_weight").val(0);
	        $("#id_available_source_quantity").val(0);
	        id_available_source_quantity_initial = 0;
	        source_sku_weight = 0;
	        $("#id_destination_sku").val($("#id_destination_sku option:first").val());
	        $("#id_destination_sku").trigger('change');
	    }
	    if(type == 'shop'){
            $("#id_source_sku").val($("#id_source_sku option:first").val());
	        $("#id_source_sku").trigger('change');
	    }
	}

	function set_weights(repackage_qty){
	    $("#id_source_repackage_quantity").val(repackage_qty);
        var available_source_weight = id_available_source_quantity_initial * source_sku_weight;
        var repackage_weight = repackage_qty * source_sku_weight;
	    if (repackage_qty > id_available_source_quantity_initial){
	        alert("Please enter repackage quantity less than available source quantity")
	        return false;
	    }
        $("#id_available_source_weight").val(available_source_weight - repackage_weight);
        $("#id_available_source_quantity").val(id_available_source_quantity_initial - repackage_qty);
	};
  });

})(django.jQuery);