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

 // $( "head" ).append(`<script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap-datepicker/1.3.0/js/bootstrap-datepicker.js"></script>`);
window.addEventListener("load", function() {
    (function($) {

        hide_show_fofo_config();
        $("select[name='shop_type'], #id_online_inventory_enabled").change(function() {
            hide_show_fofo_config();
        });
    })(django.jQuery);
});


function hide_show_fofo_config(){
    if ($("#id_shop_type").val() == "" && $("#id_online_inventory_enabled").prop('checked') == true){

        django.jQuery("#fofo_shop-group").show();
    }
    else {
            django.jQuery("#fofo_shop-group").hide();
    }

    if ($("#id_shop_type").val() == "6" && $("#id_online_inventory_enabled").prop('checked') == true){
        django.jQuery("#fofo_shop_config-group").show();
    }
    else {
        django.jQuery("#fofo_shop_config-group").hide();
    }


}