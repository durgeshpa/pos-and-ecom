(function($) {
  var list = new Array();
  var uncheckedlist = new Array();

  $(document).ready(function() {
    AppendTable();
    CallAPI();
  });

function GetURL() {
  var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '') + '/';
  var url = host + 'admin/retailer_to_sp/cart/load-dispatches/';
  return url;
}

function AppendTable(){
   $.get("/static/admin/js/CommercialShipmentsTable.html", function(data){
    $("fieldset.module.aligned").after(data);
});
}

function GetTripID() {
  var url = window.location.href;
  url = url.split("/")
  trip_id = url[url.length - 3];
  return trip_id
}

function GetResultByTripID() {
  var trip_id = GetTripID();
  $.ajax({
      url: GetURL(),
      data: {
          'trip_id': trip_id,
          'commercial': 'commercial'
      },
      complete: function(){
        $("#loading").hide();
      },
      success: function(data) {
        CheckResponse(data);
      }
  });
}

function CheckResponse(data){
  if (data['is_success']){
    CreateResponseTable(data);
  } else{
    ShowMessage(data['message']);
  }
}

function ShowMessage(msg){
  $("tbody#data").append("<tr class='form-row'><td colspan='7'>"+msg+"<td></tr>");
}

function CreateResponseTable(data){
  var trip_id = $('#id_trip_id').val();
  for (var i = 0; i < data['response_data'].length; i++) {
      var row = "row2";
      if (i % 2 === 0) {
          var row = "row1";
      }
      var pk = data['response_data'][i]['pk'];
      var trip = data['response_data'][i]['trip'];
      var order = "<td>" + data['response_data'][i]['order'] + "</td>";
      var shipment_status = "<td>" + data['response_data'][i]['shipment_status'] + "</td>";
      var invoice_no = "<td><a href='/admin/retailer_to_sp/cart/commercial/"+pk+"/shipment-details/' target='_blank'>"+ data['response_data'][i]['invoice_no'] + "</a></td>";
      var invoice_amount = "<td>" + data['response_data'][i]['invoice_amount'] + "</td>";
      var cash_to_be_collected = "<td>" + data['response_data'][i]['cash_to_be_collected'] + "</td>";
      var invoice_city = "<td>" + data['response_data'][i]['invoice_city'] + "</td>";
      var shipment_address = "<td>" + data['response_data'][i]['shipment_address'] + "</td>";
      var created_at = "<td>" + data['response_data'][i]['created_at'] + "</td>";

      $("tbody#data").append("<tr class="+ row +"><td class='original'></td>" + invoice_no + invoice_amount + cash_to_be_collected + shipment_status + invoice_city + created_at + order + shipment_address +"</tr>");
  }
}

function CallAPI(){
    GetResultByTripID();
}
})(django.jQuery);
