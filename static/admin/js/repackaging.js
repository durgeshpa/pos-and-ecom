(function($) {
    $(document).ready(function() {
    var available_source_quantity_initial;
    var available_source_weight_initial;
    var source_sku_weight;
    if ($("#id_destination_sku").val() == ''){
        $('#id_source_repackage_quantity').attr('readonly', true);
    }
    $(".calendar-shortcuts").addClass('hidden');

	$("#id_source_sku").on('change', function(){
	    reset('source');
	    if($(this).val() == ''){
	        return false;
	    }
        $.ajax({ data: ({'sku_id':$(this).val(), 'shop_id':$('#id_seller_shop').val() }) ,
            type: 'GET',
            url: '/admin/products/product/source-repackage-detail/',
            success: function(response) {
                if(response.success){
                    $("#id_available_source_quantity").val(response.available_source_quantity);
                    $("#id_available_source_weight").val(response.available_weight);
                    source_sku_weight = response.source_sku_weight;
                    available_source_quantity_initial = response.available_source_quantity;
                    available_source_weight_initial = response.available_weight;
                } else {
                    alert(response.error)
                }
            },
        });
	});

	$("#id_destination_sku").on('change', function(){
	    reset('dest')
	    if($(this).val() == ''){
	        return false;
	    }
	    $.ajax({ data: ({'sku_id':$(this).val(), 'shop_id':$('#id_seller_shop').val() }) ,
            type: 'GET',
            url: '/admin/products/product/packing-material-check/',
            success: function(response) {
                if (response.success){
                    $('#id_source_repackage_quantity').attr('readonly', false);
                } else {
                    alert(response.error)
                }
            },
        });
	});

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

	$('#id_destination_sku_quantity').on('blur', function(){
	    if($(this).val() < 0 || $(this).val() == ''){
	        $(this).val(0);
	    }
	    var packing_sku_weight_per_unit_sku = $("#id_packing_sku_weight_per_unit_sku").val();
	    if (packing_sku_weight_per_unit_sku <= 0){
	        alert("Packing SKU / Packing SKU Weight Per Unit Destination SKU Not Found");
	        return false;
	    }
	    var destination_qty = $(this).val();
	    var packing_sku_weight = $("#id_available_packing_material_weight_initial").val();
	    var packing_sku_weight_needed = destination_qty * packing_sku_weight_per_unit_sku;
	    if (packing_sku_weight_needed > packing_sku_weight){
	        alert("Packing Material Inventory Not Sufficient");
	        return false;
	    }
	    $("#id_available_packing_material_weight").val((packing_sku_weight - packing_sku_weight_needed) / 1000);
	});

	function reset(type){
	    if(type == 'shop' || type=='source'){
	        $("#id_available_source_weight").val(0);
	        $("#id_available_source_quantity").val(0);
	        available_source_quantity_initial = 0;
	        available_source_weight_initial = 0;
	        source_sku_weight = 0;
	        $("#id_destination_sku").val($("#id_destination_sku option:first").val());
	        $("#id_destination_sku").trigger('change');
	        $("#id_source_repackage_quantity").val(0);
	        $('#id_source_repackage_quantity').attr('readonly', true);
	    }
	    if(type == 'shop'){
            $("#id_source_sku").val($("#id_source_sku option:first").val());
	        $("#id_source_sku").trigger('change');
	    }
	}

	function set_weights(repackage_qty){
	    $("#id_source_repackage_quantity").val(repackage_qty);
        var repackage_weight = (repackage_qty * source_sku_weight).toFixed(3);
	    if (repackage_qty > available_source_quantity_initial){
	        alert("Please enter repackage quantity less than available source quantity")
	        return false;
	    }
        $("#id_available_source_weight").val((available_source_weight_initial - repackage_weight).toFixed(3));
        $("#id_available_source_quantity").val(available_source_quantity_initial - repackage_qty);
	};

	$("#repackaging_form").submit(function() {
      if (is_valid()) {
        if ($("#id_source_repackage_quantity").val() > available_source_quantity_initial){
	        alert("Please enter repackage quantity less than available source quantity")
	        return false;
	    } else {
            return true;
        }
      } else {
        alert("Please fill all mandatory fields!")
        return false;
      }
    });

    function is_valid(){
        var dval = $("#id_destination_sku").val();
        var sval = $("#id_source_sku").val();
        var shopval = $("#id_seller_shop").val();
        var rval = $("#id_source_repackage_quantity").val();
        if(dval == '' || sval == '' || shopval == '' || (!/^([1-9]\d*)$/.test(rval) && rval != undefined)){
            return false;
        }
        return true;
    };
  });

})(django.jQuery);