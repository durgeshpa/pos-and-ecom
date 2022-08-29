(function($) {
     $(document).ready(function() {

        $("div[id$='collapse']").fadeOut();

          $('#changelist-filter').children('h3').each(function(){

        var $title = $(this);
        $title.css( 'cursor', 'pointer' );
        $(this).next('ul').fadeOut();
        $title.click(function(){
            $title.next().fadeToggle();
        });
    });

        $("h3[id$='collapse']").each(function(){
                $(this).click(function(){
                    var id = $(this).attr('id');
                    $('div#'+id).fadeToggle();
                });
        });
    });
 })(django.jQuery);
