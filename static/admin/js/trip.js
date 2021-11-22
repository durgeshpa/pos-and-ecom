
  var selected_shipment = [];
  var list = new Array();
  var uncheckedlist = new Array();
  var initialload = true;
  var page_data={};
  var shipment_list=new Array();
  var trip_status=null;
  $(document).ready(function() {
    HideField('tr#heading');
    HideField('tr#loading');
    Select2Field('#id_seller_shop');
    //Select2Field('#id_delivery_boy');
    SubmitFormConfirmDialog();
    AddCheckedIDToList();
    GetResultOnTypingArea();
    GetResultOnChangeSellerShop();
    CallAPI();
    initTripStatus();
  });


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

function initTripStatus(){
    trip_status = $('select#id_trip_status').val()
}

$(document).ready(function() {
  $(document).on('keypress',function(e){
      var this_elem = e.target;
    if(e.which==13){
     if(e.target.id=='id_Invoice_No'){
        e.preventDefault();
        var invoice_no = $('#id_Invoice_No').val().trim();
        page_data[invoice_no].selected=true;
        CheckResponse();
        $('#id_Invoice_No').val("");
      }
    }
  });
});


function initPageData(data){
  page_data={};
  $.each(data.response_data, function(i,elem){
    if(elem.shipment_status=="Ready to Dispatch"){
      elem.selected=true;
    }
    page_data[elem.invoice_no]=elem;
  });
}

function initList(){
      list=[];
      $('.shipment_checkbox').each(function(i, elem){
          if ($(this).is(':checked')) {
            list.push(page_data[$(this).val()].pk);
          }
        });
        $('#id_selected_id').val(list);

}

function SubmitFormConfirmDialog(){
  $('form').bind('submit', function(e) {
      if ($('input[type=checkbox]:checked')) {
        initList();
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
          initPageData(data);
        }
        CheckResponse();
      }
  });
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
                initPageData(data);
                CheckResponse();
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
              success: function(data) {
                initPageData(data);
                CheckResponse();
              }
          });
      }
  });
}

function GetResultOnChangeSellerShop() {
  $("#id_seller_shop").on('change',function() {
      $('option:selected', $(this)).each(function() {
          EmptyElement('tbody#data');
          HideField('tr#heading');
          ShowField('tr#loading');
          var seller_shop_id = $("option:selected").val();
          $.ajax({
              url: GetURL(),
              data: {
                  'seller_shop_id': seller_shop_id
              },
              success: function(data) {
              if(data.is_success){
                initPageData(data);
                CheckResponse(data);
                }
                

              }
          });
      });

  });
}



function GetResultByTripID() {
  var trip_id = $('#id_trip_id').val();
  if(!trip_id){
    return false;
  }
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
        initPageData(data);
        CheckResponse();
      }

  });
}

function CheckResponse(){
  if(!$.isEmptyObject(page_data)){
    EmptyElement('tbody#data');
    ShowField('tr#heading');
    HideField('tr#loading');
    CreateResponseTable(page_data);
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

function displaySelectedCount(){
    initList();
    $("#total_invoices").text(list.length);
}
function CreateResponseTable(data){
  var trip_id = $('#id_trip_id').val();
  row="row2";
  $.each(page_data, function(i, elem){

      if(row == "row1"){
        row="row2";
      }
      else{
        row="row1";
      }
      var pk = elem.pk;
      var trip = elem.trip;
      var order = "<td>" + elem.order + "</td>";
      var shipment_status = "<td>" + elem.shipment_status + "</td>";
      if (GetTripStatus() == ('COMPLETED') || GetTripStatus() == 'CLOSED'){
        var invoice_no = "<td><a href='/admin/retailer_to_sp/orderedproduct/"+elem.pk+"/change/' target='_blank'>"+ elem.invoice_no + "</a></td>";
      }else {
        var invoice_no = "<td><a href='/admin/retailer_to_sp/dispatch/"+elem.pk+"/change/' target='_blank'>"+ elem.invoice_no + "</a></td>";
      }
      var invoice_amount = "<td>" + elem.invoice_amount + "</td>";
      var invoice_city = "<td>" + elem.invoice_city + "</td>";
      var shipment_weight = "<td>" + elem.shipment_weight + "</td>";
      var shipment_address = "<td>" + elem.shipment_address + "</td>";
      var created_at = "<td>" + elem.created_at + "</td>";
      if(elem.selected){
        var select = "<td><input type='checkbox' class='shipment_checkbox' value='"+elem.invoice_no+"' checked></td>";
      $("tbody#data").prepend("<tr class=" + row + ">" + select + invoice_no + invoice_amount + shipment_status + invoice_city + created_at + order + shipment_weight + shipment_address  +"</tr>");
      }
      else{
        select = "<td><input type='checkbox' class='shipment_checkbox' value='"+elem.invoice_no+"'></td>";
      $("tbody#data").append("<tr class=" + row + ">" + select + invoice_no + invoice_amount + shipment_status + invoice_city + created_at + order + shipment_weight + shipment_address  +"</tr>");
      }
  });
  displaySelectedCount();
  if (GetTripStatus() == 'COMPLETED'|| (GetTripStatus() == 'STARTED' && trip_status == 'STARTED') || GetTripStatus() == 'CLOSED'){
    $(".shipment_checkbox").prop("checked", true);
    $(".shipment_checkbox").attr("disabled", true);
    $(".selected_invoice_count").hide();
  }
  initialload = false;
}

function EmptyElement(id){
  $(id).empty();
}

function AddCheckedIDToList(){
  $(document).on('click', '.shipment_checkbox', function() {
      if ($(this).is(':checked')) {
          page_data[$(this).val()].selected=true
      } else {
          page_data[$(this).val()].selected=false
      }
      displaySelectedCount();
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
