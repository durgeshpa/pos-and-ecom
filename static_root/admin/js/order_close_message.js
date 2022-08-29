(function($) {
    $(document).ready(function() {
      if (!$('#id_close_order').is(':disabled')) {
        $("input[type='submit']").on("click", function(e){
            e.preventDefault();
            swal({
              closeOnClickOutside: false,
              closeOnEsc: false,
              text: "Do you want to close the order?",
              dangerMode: true,
              buttons: ['No', 'Yes'],
            })
            .then(willDelete => {
              if (willDelete) {
                $('#id_close_order').attr('checked', true);
                  swal({
                    closeOnClickOutside: false,
                    closeOnEsc: false,
                    text: "You will be not able to create further shipments!",
                    icon: "warning",
                    buttons: ['Cancel', 'OK'],
              })
                .then(willDelete => {
                if (willDelete){
                  $('form#shipment_form').submit();
                } else {
                  $('#id_close_order').attr('checked', false);
                  $('form#shipment_form').submit();
                }
              });
              } else {
                $('#id_close_order').attr('checked', false);
                $('form#shipment_form').submit();
              }
            });
        });
      }
	$('#id_close_order').on('change', function(){
   			if(this.checked) {
        		swal({
              closeOnClickOutside: false,
              closeOnEsc: false,
        			title: "Are you sure?",
        			text: "You will be not able to create further shipments!",
        			icon: "warning",
  					button: true,
				});
    		}
		})
    });
})(django.jQuery);
