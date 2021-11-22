if (!$) {
    $ = django.jQuery;
};

    $(document).ready(function() {
      $("#changelist-form").submit(function( event ) {
        if ($(this).find('select[name=action]').val() === 'approve_product_price'){
          if ($("#changelist-form input:checkbox:checked").length > 0)
{
        event.preventDefault();
        $(this).find('select[name=action]').each(function(){
          if ($(this).val() === 'approve_product_price') {
            swal({
              title: "Are you sure?",
              text: "Once approved, the products prices will be updated!",
              icon: "warning",
              buttons: true,
              dangerMode: true,
            })
            .then((willDelete) => {
              if (willDelete) {
            $("#changelist-form").unbind('submit').submit()  }
            });
          }
        });    
}


      }

});

    });

