/*
function autoSubmit(){
    $('#invoice').keydown(function() {
    var key = e.which;
    if (key == 13) {
        $('#invoice').submit(); // Submit form code
     }
});
}
*/
  var selected_shipment = [];
  var list = new Array();
  var uncheckedlist = new Array();
  var initialload = true;
  var page_data={};
  var shipment_list=new Array();
  $(document).ready(function() {
    HideField('tr#heading');
    HideField('tr#loading');
    Select2Field('#id_seller_shop');
    Select2Field('#id_delivery_boy');
    SubmitFormConfirmDialog();
    GetResultOnTypingArea();
    CallAPI();
  });

//$('input:text').focus(
  //  function(){
    //    $(this).val('');
    //});

var data1 =[];

function Select2Field(id) {
  $(id).select2();
}

function HideField(id){
  $(id).hide();
}

function ShowField(id){
  $(id).show();
}

$(document).ready(function() {
    $(document).on('keypress',function(e){
        var this_elem = e.target;
      if(e.which==13){
         if(e.target.id=='id_Invoice_No'){
         e.preventDefault();
      var invoice_no = $('#id_Invoice_No').val().trim();
      var seller_shop = $('#id_seller_shop').val();
      var shipment_data = page_data.pending_shipments.response_data;
      //list.push(invoice_no);
      invoice_filter =function(shipment_data, invoice_no){return shipment_data.filter(function(item){
            return item.invoice_no==invoice_no
       })};
       $.each(invoice_filter(shipment_data, invoice_no), function(i, elem){
            elem.selected=true;
            if(list.indexOf(elem.pk)==-1)
            {
                list.push(elem.pk);
            }
            $('#id_selected_id').val(list);
       });
        CheckResponse();
        $('#id_Invoice_No').val("");
//        else{
//        $.ajax({
//            url: GetURL(),
//            data:{
//                'invoice_no':invoice_no
//               },
//               success: function(data){
//               CheckResponse(page_data.pending_shipments.response_data.push(data.response_data[0]));
//               $('#id_Invoice_No').val("");
//               }
//        });
//        }
    }}
    });
    });


/*function GetResultOnTypingArea(){
  $('#id_Invoice_No').on('input', function() {
      this_elem = $(this);
      //EmptyElement('tbody#data');
     //HideField('tr#heading');
      //ShowField('tr#loading');
      var invoice_no = $('#id_Invoice_No').val();
      var seller_shop = $('#id_seller_shop').val();
      //var trip_id = $('#id_trip_id').val();

      if (seller_shop.length == 0) {
          alert("Please select Seller Shop first!");
      } else {
          $.ajax({
              url: GetURL(),
              data: {
                  'invoice_no': invoice_no,

              },
              success: function(data) {
                CheckResponse(data);
//              this_elem.preventDefault();
//               this_elem.stopPropogation();
               this_elem.empty();
              }
          });
      }
  });
}
*/









function GetResultByTripAndSellerShop() {
  var seller_shop_id = $('select#id_seller_shop').val();
  var trip_id = $('#id_trip_id').val();
  EmptyElement('tbody#data');
  HideField('tr#heading');
  ShowField('tr#loading');
  var seller_shop_id = $("option:selected").val();
  $.ajax({
      url: GetURL(),
     data: {
          'seller_shop_id': seller_shop_id,
          'trip_id': trip_id,


      },
      success: function(data) {
        if(data.is_success){
            page_data['pending_shipments'] = data;
        }
        else{}
        CheckResponse();
      }
  });
}



function SubmitFormConfirmDialog(){
  $('form').bind('submit', function(e) {
      if ($('input[type=checkbox]:checked')) {
        list=[];
        $('.shipment_checkbox').each(function(i, elem){
            if ($(this).is(':checked')) {
                debugger;
              list.push($(this).val());
              $('#id_selected_id').val(list);
            }
          });





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
      HideField('tr#heading');
      ShowField('tr#loading');
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
function GetResultOnTypingPincode(){
  $('#id_search_by_pincode').on('input', function() {
      EmptyElement('tbody#data');
      HideField('tr#heading');
      ShowField('tr#loading');
      var area = $(this).val();
      var seller_shop = $('#id_seller_shop').val();
      var trip_id = $('#id_trip_id').val();

      if (seller_shop.length == 0) {
          alert("Please select Seller Shop first!");
      } else {
          $.ajax({
              url: GetURL(),
          /*   data: {
                  'seller_shop_id': seller_shop,
                  'pincode': area,
                  'trip_id': trip_id

              },*/
              success: function(data) {
                CheckResponse(data);
              }
          });
      }
  });
}



function GetResultByTripID() {
  var trip_id = $('#id_trip_id').val();
  EmptyElement('tbody#data');
  HideField('tr#heading');
  ShowField('tr#loading');
  var seller_shop_id = $("option:selected").val();
  $.ajax({
      url: GetURL(),
      data: {
          'trip_id': trip_id
      },
      success: function(data) {
        page_data['pending_shipments'] = data;
        CheckResponse();
      }

  });
}

function CheckResponse(){
    data = page_data.pending_shipments;
  if (data['is_success']){
    EmptyElement('tbody#data');
    ShowField('tr#heading');
    HideField('tr#loading');
    CreateResponseTable(data);
  } else{
    EmptyElement('tbody#data');
    HideField('tr#heading');
    HideField('tr#loading');
    //ShowMessage(data['message']);
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
      var pincode = "<td>" + data['response_data'][i]['pincode'] + "</td>";
      var created_at = "<td>" + data['response_data'][i]['created_at'] + "</td>";

      if(data['response_data'][i]['shipment_status']=="Ready to Dispatch"){
            data['response_data'][i]['selected'] = true;
            if(list.indexOf(data['response_data'][i]['pk'])==-1){
                list.push(data['response_data'][i]['pk']);
            }
      }
      if(data['response_data'][i]['selected']){
        var select = "<td><input type='checkbox' class='shipment_checkbox' value='"+pk+"' checked></td>";
      $("tbody#data").prepend("<tr class=" + row + ">" + select + invoice_no + invoice_amount + shipment_status + invoice_city + created_at + order + shipment_address + pincode +"</tr>");
      }
      else{
        select = "<td><input type='checkbox' class='shipment_checkbox' value='"+pk+"'></td>";
      $("tbody#data").append("<tr class=" + row + ">" + select + invoice_no + invoice_amount + shipment_status + invoice_city + created_at + order + shipment_address + pincode +"</tr>");
      }

  }
    $('#id_selected_id').val(list);
    $("#total_invoices").text(list.length);
  initialload = false;
  GetUncheckedFields();
}

function EmptyElement(id){
  $(id).empty();
}


function GetUncheckedFields() {
  uncheckedlist = [];
  $('#id_unselected_id').val('');
  $('.shipment_checkbox').each(function(){
    if (!$(this).is(':checked')) {
      uncheckedlist.push($(this).val());
      $('#id_unselected_id').val(uncheckedlist);
    }
  });
}

function DisableCheckBox() {
  $('.shipment_checkbox').each(function(){
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
