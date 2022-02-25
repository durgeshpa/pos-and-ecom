//django.jQuery( document ).ready(function() {
//    console.log("Inside on change");
//    hide_show_fofo_config();
//    django.jQuery("#id_online_inventory_enabled").change(function(val) {
//        hide_show_fofo_config();
//    });
//    django.jQuery("#id_shop_type").change(function(val) {
//        hide_show_fofo_config();
//    });
//    function hide_show_fofo_config(){
//    alert("hello");
//        if ($("#id_shop_type").val() == "6" && $("#id_online_inventory_enabled").prop('checked') == true){
//            django.jQuery("#fofo_shop-group").show();
//        }
//        else {
//            django.jQuery("#fofo_shop-group").hide();
//        }
//    }
//});

window.addEventListener("load", function() {
    (function($) {
        hide_show_fofo_config();
        $("select[name='shop_type'], #id_online_inventory_enabled").change(function() {
            hide_show_fofo_config();
        });
    })(django.jQuery);
});

function hide_show_fofo_config(){
    if ($("#id_shop_type").val() == "6" && $("#id_online_inventory_enabled").prop('checked') == true){
        django.jQuery("#fofo_shop-group").show();
    }
    else {
        django.jQuery("#fofo_shop-group").hide();
    }
}