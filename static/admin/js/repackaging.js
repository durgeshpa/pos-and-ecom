(function($) {
    $(document).ready(function() {
    var id_available_source_quantity_initial = 0;
    var source_sku_weight = 0;
    var destination_sku_weight = 0;

    $('#id_repackage_weight').attr('readonly', true);
    $('input[name=_continue]').val('Save and view');

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

	$("#id_destination_sku").on('change', function(){
	    reset('dest');
	    if($(this).val() == ''){
	        return false;
	    }
        $.ajax({ data: ({'sku_id':$(this).val() }) ,
            type: 'GET',
            url: '/admin/products/product/destination-repackage-detail/',
            success: function(response) {
                if(response.success){
                    if (response.destination_sku_weight == 0 || response.destination_sku_weight == ''){
                        alert("Destination SKU weight value not found");
                        return false;
                    }
                    $('#id_repackage_weight').attr('readonly', false);
                    destination_sku_weight = response.destination_sku_weight;
                } else {
                    alert(response.error)
                }
            },
        });
	});

	$("#id_seller_shop").on('change', function(){
        reset('shop');
	});

	$('#id_repackage_weight').on('blur', function(){
	    if($(this).prop('readonly')){
	        return false;
	    }
	    if($(this).val() < 0 || $(this).val() == ''){
	        $(this).val(0);
	    }
	    var repackage_weight = $(this).val();
        set_weights(repackage_weight);
	});

	function reset(type){
	    $("#id_repackage_weight").val(0);
	    $("#id_destination_sku_quantity").val(0);
	    destination_sku_weight = '';
	    $('#id_repackage_weight').attr('readonly', true);
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

	function set_weights(repackage_weight){
	    $("#id_repackage_weight").val(repackage_weight);
        var available_source_weight = id_available_source_quantity_initial * source_sku_weight;
	    if (repackage_weight > available_source_weight){
	        alert("Please enter weight value less than available source weight")
	        return false;
	    }
	    if (repackage_weight % source_sku_weight != 0 && repackage_weight != 0) {
            alert("Please enter weight value that is multiple of Source SKU’s weight value")
            return false;
	    }
        $("#id_available_source_weight").val(available_source_weight - repackage_weight);
        $("#id_available_source_quantity").val($("#id_available_source_weight").val() / source_sku_weight);
   	    $("#id_destination_sku_quantity").val(repackage_weight / destination_sku_weight);
	};
  });


})(django.jQuery);

var final_fg;
var conversion;

function add_cost(obj){
    final_fg = 0;
    conversion = 0;
    $(obj).parents('.dynamic-repackagingcost_set').find('input[type=number]').each(function () {
        var obj_class = $(this).parent('td').attr('class');
        if(jQuery.inArray(obj_class, ['field-particular', 'field-final_fg_cost', 'field-conversion_cost']) == -1){
            var value = parseFloat($(this).val()) || 0;
            if(obj_class == 'field-raw_material'){
                final_fg += value;
            } else {
                final_fg += value;
                conversion += value;
            }
        }
    });
    $(obj).parents('.dynamic-repackagingcost_set').find('.field-final_fg_cost').find("input[type=number]").val(final_fg);
    $(obj).parents('.dynamic-repackagingcost_set').find('.field-conversion_cost').find("input[type=number]").val(conversion);
}