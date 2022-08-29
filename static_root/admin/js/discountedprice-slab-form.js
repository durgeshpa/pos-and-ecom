
jQuery(function($) {
    function toggle_manual_price_update(value)
    {
        var div =  document.getElementById('id_selling_price');
        if (value == true){
            div.readOnly = false;
            document.getElementById('id_selling_price').value='';
        }else if(value == false){
            div.readOnly = true;
            getSellingPriceDetails();
        }
    }
    toggle_manual_price_update($('#id_is_manual_price_update').prop('checked'))

    $('#id_is_manual_price_update').click(function() {
        toggle_manual_price_update(this.checked);
    });

});
