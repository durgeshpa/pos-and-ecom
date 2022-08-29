(function($) {
    $(document).ready(function() {
      $("#changelist-form").submit(function( event ) {
        if ($(this).find('select[name=action]').val() === 'change_trip_status'){

        event.preventDefault();
        $(this).find('select[name=action]').each(function(){
          if ($(this).val() === 'change_trip_status') {
            swal({
              title: "Have you received the amount?",
              text: "Once status changed, you will not be able to revert back!",
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

});

    });
})(django.jQuery);
