$(function () {
  var total_files = 0;

  $(".js-upload-photos").click(function () {
    $("#fileupload").click();

  });

var number_of_files = 0;
var aborted_files = 0;
  $("#fileupload").fileupload({

    dataType: 'json',
    sequentialUploads: true,

    // start: function (e) {
    //   $("#modal-progress").modal("show");
    // },

    progressall: function (e, data) {
      var progress = parseInt(data.loaded / data.total * 100, 10);
      var strProgress = progress + "%";
      $(".progress-bar").css({"width": strProgress});
      $(".progress-bar").text(strProgress);

    },

    done: function (e, data) {
      if (data.result.is_valid) {
        $("#gallery tbody").prepend(
          // "<tr><td><a href='" + data.result.url + "'>" + data.result.name + "</a></td></tr>"
          "<tr><td><a href='" +
          data.result.url + "'>" +
          data.result.name +
          "</a></td><td>Product Name: " +
          data.result.product_name +
          "</td><td>Product ID: " +
          data.result.product_sku +
          "</td></tr>"
        )
      }
    },

    stop: function (e) {
      $("#modal-progress").modal("hide");

    },

    always: function (e, data) {
      total_files = total_files + 1;
      if (data.result.error) {
        aborted_files = aborted_files + 1;
        $("#gallery tbody").prepend(
          "<tr><td><a class='alert-danger' href='" + data.result.url + "'>" + data.result.name + "</a></td><td></td><td></td></tr>"
        )
      }
      var files_uploaded = total_files - aborted_files;
      $('.total-files b').text(total_files);
      $('.files-uploaded b').text(files_uploaded);
      $('.aborted b').text(aborted_files);

    },
  });


});
