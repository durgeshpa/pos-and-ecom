
jQuery(function($) {
        document.getElementById('id_price_slabs-0-start_value').value = 1;
        document.getElementById('id_price_slabs-1-end_value').value = 0;
        $('#id_price_slabs-1-start_value').change(function() {
            document.getElementById('id_price_slabs-0-end_value').value = $('#id_price_slabs-1-start_value').val()-1;
        });
});