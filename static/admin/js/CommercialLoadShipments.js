(function($) {
  var list = new Array();
  var uncheckedlist = new Array();

  $(document).ready(function() {
    SubmitFormConfirmDialog();
    GetResultOnTypingArea();
    AddCheckedIDToList();
    CallAPI();
  });


function SubmitFormConfirmDialog(){
  $('form').bind('submit', function(e) {
      if ($('input[type=checkbox]:checked').length) {
          var c = confirm("Click OK to continue?");
          return c;
      } else {
          e.preventDefault(e);
          alert("Please select at least one shipment");

      }
  }); 
}

function GetURL() {
  var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '') + '/';
  var url = host + 'admin/retailer_to_sp/cart/load-dispatches/';
  return url;
}

function GetResultOnTypingArea(){
  $('#id_search_by_area').on('input', function() {
      EmptyElement('tbody#data');
      var area = $(this).val();
      var seller_shop = $('#id_seller_shop').val();
      var trip_id = $('#id_trip_id').val();

      if (seller_shop.length == 0) {
          alert("Please select Seller Shop first!");
      } else {
          $.ajax({
              url: GetURL(),
              data: {
                  'seller_shop_id': seller_shop,
                  'area': area,
                  'trip_id': trip_id

              },
              success: function(data) {
                CheckResponse(data);
              }
          });
      }
  });
}

function GetResultByTripAndSellerShop() {
  var seller_shop_id = $('select#id_seller_shop').val();
  var trip_id = $('#id_trip_id').val();
  EmptyElement('tbody#data');
  var seller_shop_id = $("option:selected").val();
  $.ajax({
      url: GetURL(),
      data: {
          'seller_shop_id': seller_shop_id,
          'trip_id': trip_id
      },
      success: function(data) {
        CheckResponse(data);
      }
  });
}

function GetResultByTripID() {
  var trip_id = $('#id_trip_id').val();
  EmptyElement('tbody#data');
  var seller_shop_id = $("option:selected").val();
  $.ajax({
      url: GetURL(),
      data: {
          'trip_id': trip_id
      },
      success: function(data) {
        CheckResponse(data);
      }
  });
}

function CheckResponse(data){
  if (data['is_success']){
    EmptyElement('tbody#data');
    CreateResponseTable(data);
  } else{
    EmptyElement('tbody#data');
    ShowMessage(data['message']);
  }
}

function ShowMessage(msg){
  $("tbody#data").append("<tr><td>"+msg+"<td></tr>");
}

function CreateResponseTable(data){
  var trip_id = $('#id_trip_id').val();
  for (var i = 0; i < data['response_data'].length; i++) {
      var row = "row1";
      if (i % 2 === 0) {
          var row = "row2";
      }
      var pk = data['response_data'][i]['pk'];
      var trip = data['response_data'][i]['trip'];
      if(trip==trip_id){
        if (GetTripStatus() != ('READY')){
            var select = "<td><input type='checkbox' class='shipment_checkbox' value='"+pk+"' checked disabled='disabled'></td>";
        }
        else{
          var select = "<td><input type='checkbox' class='shipment_checkbox' value='"+pk+"' checked></td>";
        }
        list.push(pk);
        $('#id_selected_id').val(list);
      }
      else{
        var select = "<td><input type='checkbox' class='shipment_checkbox' value='"+pk+"'></td>";
      }
      var order = "<td>" + data['response_data'][i]['order'] + "</td>";
      var shipment_status = "<td>" + data['response_data'][i]['shipment_status'] + "</td>";
      if (GetTripStatus() == ('COMPLETED')){
        var invoice_no = "<td><a href='/admin/retailer_to_sp/orderedproduct/"+pk+"/change/' target='_blank'>"+ data['response_data'][i]['invoice_no'] + "</a></td>";
      }else {
        var invoice_no = "<td><a href='/admin/retailer_to_sp/dispatch/"+pk+"/change/' target='_blank'>"+ data['response_data'][i]['invoice_no'] + "</a></td>";
      }
      var invoice_amount = "<td>" + data['response_data'][i]['invoice_amount'] + "</td>";
      var invoice_city = "<td>" + data['response_data'][i]['invoice_city'] + "</td>";
      var shipment_address = "<td>" + data['response_data'][i]['shipment_address'] + "</td>";
      var created_at = "<td>" + data['response_data'][i]['created_at'] + "</td>";

      $("tbody#data").append("<tr class=" + row + ">" + select + invoice_no + invoice_amount + shipment_status + invoice_city + created_at + order + shipment_address +"</tr>");
  }
}

function EmptyElement(id){
  $(id).empty();
}

function AddCheckedIDToList(){
  $(document).on('click', '.shipment_checkbox', function() {
      if ($(this).is(':checked')) {
          GetUncheckedFields();
          list.push($(this).val());
          $('#id_selected_id').val(list);
      } else {
          GetUncheckedFields();
          list.pop($(this).val());
          $('#id_selected_id').val(list);
      }
  });
}

function GetUncheckedFields() {
  $('.shipment_checkbox').each(function(){
    if (!$(this).is(':checked')) {
      uncheckedlist.push($(this).val());
      $('#id_unselected_id').val(uncheckedlist);
    }
  });
}

function DisableCheckBox() {
  $('.shipment_checkbox').each(function(){
    console.log("ADFAS");
    $(this).attr('disabled','disabled');
  });
}

function GetTripStatus(){
  return $('select#id_trip_status').val();
}

function CallAPI(){
  if (GetTripStatus() != ('READY')){
    GetResultByTripID();
  }
  else{
    GetResultByTripAndSellerShop();
  }
}
})(django.jQuery);
