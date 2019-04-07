
(function($) {
    'use strict';
    $(document).ready(function() {
        OnChangeShopType();
        ShowField(".field-shop_code");
        ShowField(".field-warehouse_code");
    });

    function OnChangeShopType(){
        $("#id_shop_type").change(function() {
            CheckShopType(this.value);
        });
    }

    function CheckShopType(value){
        var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
        $.ajax({ data: ({'shop_type_id': value}) ,
            type: 'GET',
            dataType: 'json',
            url: host+'admin/shops/shop/get-shop-type/',
            success: function(response) {

                 if(response['success']) {
                    if (response['shop_type'] != 'r') {
                        ShowField(".field-shop_code");
                        ShowField(".field-warehouse_code");
                    }else {
                        HideField(".field-shop_code");
                        HideField(".field-warehouse_code");
                    }
                 }
            },
            error: function (request, status, error) {
                 console.log(request.responseText);
            }
        });        
    }

    function ShowField(value){
        AddRequiredClass(value);
        $(value).show();
    }

    function HideField(value){
        RemoveRequiredClass(value);
        $(value).hide();
    }

    function AddRequiredClass(value){
        $(value).find('label').addClass('required');
    }

    function RemoveRequiredClass(value){
        $(value).find('label').removeClass('required');
    }

})(django.jQuery);