(function($) {
    $(document).ready(function() {
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