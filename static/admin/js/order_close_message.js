(function($) {
    $(document).ready(function() {
        $('form').bind('submit', function (e) {
                e.preventDefault(e);
                swal("Here's the title!", "...and here's the text!");
            
        });
    });
})(django.jQuery);