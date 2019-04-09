(function($) {
    $(document).ready(function() {
        $("input[type='submit']").on("click", function(e){
            e.preventDefault();
            swal({
              text: "Do you want to close the order?",
              dangerMode: true,
              buttons: ['No', 'Yes'],
            })
            .then(willDelete => {
              if (willDelete) {
                $('#id_close_order').attr('checked', true);
                  swal({
                    text: "You will be not able to create further shipments!",
                    icon: "warning",
                    buttons: ['Cancel', 'OK'],
              })
                .then(willDelete => {
                if (willDelete){
                  $("form[id='shipment_form']").submit();
                } else {
                  $('#id_close_order').attr('checked', false);
                  $("form[id='shipment_form']").submit();
                }
              });
              } else {
                $('#id_close_order').attr('checked', false);
                $("form[id='shipment_form']").submit();
              }
            });
        });
		$('#id_close_order').on('change', function(){
   			if(this.checked) {
        		swal({
        			title: "Are you sure?",
        			text: "You will be not able to create further shipments!",
        			icon: "warning",
  					button: true,
				});
    		}
		})
    });
})(django.jQuery);