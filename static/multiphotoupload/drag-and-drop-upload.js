$(function () {

  $(".js-upload-photos").click(function () {
    $("#fileupload").click();
  });

  $("#fileupload").fileupload({
    dataType: 'json',
    done: function (e, data) {
      if (data.result.is_valid) {
        $("#gallery tbody").prepend(
          // "<tr><td><a href='" + data.result.url + "'>" + data.result.name + "</a></td></tr>"
          "<tr><td><a href='" +
          data.result.url + "'>" +
          data.result.name +
          "</a></td><td>Product Name: " +
          data.result.product_name +
          "</td><td>Product SKU: " +
          data.result.product_sku +
          "</td></tr>"
        )
      }
    }
  });

});
