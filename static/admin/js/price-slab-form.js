
jQuery(function($) {
        document.getElementById('price_slabs-group').style.display = "block";
        document.getElementById('id_price_slabs-0-start_value').value = 0;
        function toggle_price_slab(value)
        {
            var div =  document.getElementById('price_slabs-group');
            if (value == false){
                div.style.display = "none";
                document.getElementById('id_price_slabs-0-end_value').value=0;
                document.getElementById('id_price_slabs-1-start_value').value='';
                document.getElementById('id_price_slabs-1-end_value').value='';
                $('.single_slab').show()
            }else if(value == true){
                 div.style.display = "block";
                $('.single_slab').hide()
                getProductDetails()
                document.getElementById('id_price_slabs-1-end_value').value = 0;
            }
        }
        toggle_price_slab($('#id_slab_price_applicable').prop('checked'))
        $('#id_price_slabs-1-start_value').change(function() {
            document.getElementById('id_price_slabs-0-end_value').value = $('#id_price_slabs-1-start_value').val()-1;
        });

        $('#id_slab_price_applicable').click(function() {
            toggle_price_slab(this.checked)
        });

        $('#id_selling_price').change(function() {
            document.getElementById('id_price_slabs-0-selling_price').value = $('#id_selling_price').val();
        });
        $('#id_offer_price').change(function() {
            document.getElementById('id_price_slabs-0-offer_price').value = $('#id_offer_price').val();
        });

        $('#id_offer_price_start_date').change(function() {
            document.getElementById('id_price_slabs-0-offer_price_start_date').value = $('#id_offer_price_start_date').val();
        });
        $('#id_offer_price_end_date').change(function() {
            document.getElementById('id_price_slabs-0-offer_price_end_date').value = $('#id_offer_price_end_date').val();
        });
});
