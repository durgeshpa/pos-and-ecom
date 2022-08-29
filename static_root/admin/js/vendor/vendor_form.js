
$(document).ready(function(){
  $('select#id_state').select2();
  $('select#id_city').select2();

    $("select#id_state").change(function(){
        var selectedState= $(this).children("option:selected").val();
        var url = $("#id_city").attr("data-cities-url");

        $.ajax({
          url: url,
          data: {
            'state': selectedState
          },
          success: function (data) {
            $("#id_city").html(data);

          }
        });
      });
});
