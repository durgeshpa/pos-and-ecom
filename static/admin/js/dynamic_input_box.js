(function ($) {
   $(document).ready(function() {

        var testdiv = $("input[name=order_no]"); //order_no
        $("input").keydown( function(){
            var ME = $(this);
           testdiv.html( ME.val() + "--");
           var txtlength = testdiv.width();
           ME.css({width: txtlength  }); 
        });

    });

})(django.jQuery);