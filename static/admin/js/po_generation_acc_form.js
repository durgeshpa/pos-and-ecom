(function ($) {
    $(document).ready(function() {
        var row = 0
        var dt = ""
        var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
        $.ajax({ data: ({'po':$('#id_cart_list-0-cart').val()}) ,
                type: 'GET',
                dataType: 'json',
                url: host+'admin/gram_to_brand/cart/message-list/',
                success: function(response) {
                    // Po buttons visiblity code
                    console.log(response['po_status'])
                    if(response['po_status']== 'PDA') {
                        $(':input[name="_approve"]').prop('disabled', false);
                    }else{
                        $(':input[name="_approve"]').prop('disabled', true);
                    }

                    $("#loading").hide();
                    if(response['is_success']) {
                        $("#data").append("<tr class='row0'><td>"+response['response_data'][0].user+"</td><td>"+response['response_data'][0].message+"</td><td>"+response['response_data'][0].created_at+"</td></tr>")
                    }
                    else{
                        $("#data").append("<tr class='row0'><td>-</td><td>-</td><td>-</td></tr>")
                    }
                },
                error: function (request, status, error) {
                     console.log(request.responseText);
                }
            });

        $('.submit-row').on('click','input[type=submit]', function(e){
            var c = confirm("Are you sure?");
            return c;
        });



    });
})(django.jQuery);
