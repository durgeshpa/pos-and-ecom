
  var selected_shipment = [];
  var list = new Array();
  var return_list = new Array();
  var uncheckedlist = new Array();
  var initialload = true;
  var page_data={};
  var return_page_data = {};
  var shipment_list=new Array();
  var returns_list = new Array();
  var trip_status=null;
  $(document).ready(function() {
    HideField('tr#heading');
    HideField('tr#loading');
    Select2Field('#id_seller_shop');
    //Select2Field('#id_delivery_boy');
    SubmitFormConfirmDialog();
    AddCheckedIDToList();
    GetResultOnTypingArea();
//    GetResultOnChangeSellerShop();
//    GetResultOnChangeSourceShop();
    GetReturnResultOnChangeSellerShop();
    CallAPI();
    CallReturnAPI();
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

const initReturnPageData = (data) => {
  return_page_data = {};
  $.each(data.response_data, (i, el) => {
    if (el.return_status == "RETURN_INITIATED") {
      el.selected = true;
    }
    return_page_data[el.return_no] = el;
  });
}

function initList(){
    list=[];
    return_list = [];
    $('.shipment_checkbox').each(function(i, elem){
        if ($(this).is(':checked')) {
          list.push(page_data[$(this).val()].pk);
        }
      });
      $('#id_selected_id').val(list);
    $('.return_checkbox').each(function(i, elem){
      if ($(this).is(':checked')) {
        return_list.push(return_page_data[$(this).val()].id);
      }
    });
    $('#id_return_selected_id').val(return_list);
}

function SubmitFormConfirmDialog(){
  $('form').bind('submit', function(e) {
      if ($('input[type=checkbox]:checked')) {
        initList();
          var c = confirm("Click OK to continue?");
         return c;
      } else {
         e.preventDefault(e);
        alert("Please select at least one shipment or return");

     }
  });
}

function GetURL() {
  var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '') + '/';
  var url = host + 'admin/retailer_to_sp/cart/load-dispatches/';
  return url;
}

function GetReturnListURL(){
  var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '') + '/';
  var url = host + 'admin/retailer_to_sp/cart/load-return-orders/';
  return url;
}


function GetResultByTripAndSellerShop() {
  var seller_shop_id = $('select#id_seller_shop').val();
  var source_shop_id = $('select#id_source_shop').val();
  var trip_id = $('#id_trip_id').val();
  EmptyElement('tbody#data');
  HideField('tr#heading');
  ShowField('tr#loading');
//  var seller_shop_id = $("option:selected").val();
//  var source_shop_id = $("option:selected").val();
  $.ajax({
      url: GetURL(),
     data: {
          'seller_shop_id': seller_shop_id,
          'source_shop_id': source_shop_id,
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

const GetReturnResultByTripAndSellerShop = () => {
  const seller_shop_id = $('select#id_seller_shop').val();
  const trip_id = $('#id_trip_id').val();
  EmptyElement('tbody#data');
  HideField('tr#heading');
  ShowField('tr#loading');
  $.ajax({
    url: GetReturnListURL(),
    data: {
      'seller_shop_id': seller_shop_id,
      'trip_id': trip_id
    },
    success: (data) => {
      if (data.is_success) {
        initReturnPageData(data);
      }
      CheckReturnResponse();
    }
  })
}

function GetResultOnTypingArea(){
  $('#id_search_by_area').on('input', function() {
      EmptyElement('tbody#data');
      HideField('tr#heading');
      ShowField('tr#loading');
      var area = $(this).val();
      var seller_shop = $('#id_seller_shop').val();
      var source_shop = $('#id_source_shop').val();
      var trip_id = $('#id_trip_id').val();

      if (seller_shop.length == 0) {
          alert("Please select Seller Shop first!");
      } else {
          $.ajax({
              url: GetURL(),
              data: {
                  'seller_shop_id': seller_shop,
                  'source_shop_id': source_shop,
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
      var source_shop = $('#id_source_shop').val();
      var trip_id = $('#id_trip_id').val();

      if (seller_shop.length == 0) {
          alert("Please select Seller Shop first!");
      } if (source_shop.length == 0) {
          alert("Please select Source Shop first!");
      }  else {
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
//
//function GetResultOnChangeSellerShop() {
//  $("#id_seller_shop").on('change',function() {
//      $('option:selected', $(this)).each(function() {
//          EmptyElement('tbody#data');
//          HideField('tr#heading');
//          ShowField('tr#loading');
//          var seller_shop_id = $("option:selected").val();
//          $.ajax({
//              url: GetURL(),
//              data: {
//                  'seller_shop_id': seller_shop_id
//              },
//              success: function(data) {
//              if(data.is_success){
//                initPageData(data);
//                CheckResponse(data);
//                }
//
//
//              }
//          });
//      });
//
//  });
//}

function GetResultOnChangeSourceShop() {
          EmptyElement('tbody#data');
          HideField('tr#heading');
          ShowField('tr#loading');
          var seller_shop_id = $('#id_seller_shop').val();
          var source_shop_id = $('#id_source_shop').val();
          $.ajax({
              url: GetURL(),
              data: {
                  'seller_shop_id': seller_shop_id,
                  'source_shop_id': source_shop_id
              },
              success: function(data) {
              if(data.is_success){
                initPageData(data);
                CheckResponse(data);
                }
              }
          });
}

const GetReturnResultOnChangeSellerShop = () => {
  $("#id_seller_shop").on('change',function() {
  EmptyElement('tbody#returns_data');
  HideField('tr#returns_heading');
  ShowField('tr#returns_loading');
  var seller_shop_id = $('#id_seller_shop').val();
  $.ajax({
      url: GetReturnListURL(),
      data: {
          'seller_shop_id': seller_shop_id
      },
      success: function(data) {
      if(data.is_success){
        initReturnPageData(data);
        CheckReturnResponse(data);
        }
      }
  });
})
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
        console.log(data)
        initPageData(data);
        CheckResponse();
      }

  });
}

function GetReturnResultByTripID() {
  var trip_id = $('#id_trip_id').val();
  if(!trip_id){
    return false;
  }
  EmptyElement('tbody#returns_data');
  HideField('tr#returns_heading');
  ShowField('tr#returns_loading');
  var seller_shop_id = $("option:selected").val();
  $.ajax({
      url: GetReturnListURL(),
      data: {
          'trip_id': trip_id
      },
      success: function(data) {
        initReturnPageData(data);
        CheckReturnResponse();
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

const CheckReturnResponse = () => {
  console.log(return_page_data)
  if(!$.isEmptyObject(return_page_data)){
    EmptyElement('tbody#returns_data');
    ShowField('tr#returns_heading');
    HideField('tr#returns_loading');
    CreateReturnResponseTable(return_page_data);
  } else{
    EmptyElement('tbody#returns_data');
    HideField('tr#returns_heading');
    HideField('tr#returns_loading');
    //ShowMessage(data['message']);
  }
}

function ShowMessage(msg){
  $("tbody#data").append("<tr><td>"+msg+"<td></tr>");
}

function displaySelectedCount(){
    initList();
    $(".total_invoices").text(list.length);
    $(".total_returns").text(return_list.length);
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
      if (GetTripSourceShopType() == 'dc'){
        var invoice_no = "<td>"+ elem.invoice_no + "</td>";
      }
      else {
          if (GetTripStatus() == ('COMPLETED') || GetTripStatus() == 'CLOSED'){
            var invoice_no = "<td><a href='/admin/retailer_to_sp/orderedproduct/"+elem.pk+"/change/' target='_blank'>"+ elem.invoice_no + "</a></td>";
          }else {
            var invoice_no = "<td><a href='/admin/retailer_to_sp/dispatch/"+elem.pk+"/change/' target='_blank'>"+ elem.invoice_no + "</a></td>";
          }
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

const CreateReturnResponseTable = (return_data) => {
  const trip_id = $('#id_trip_id').val();
  row = "row2";
  $.each(return_page_data, (i, el) => {
    if(row == "row1"){
      row="row2";
    }
    else{
      row="row1";
    }
    var pk = el.pk;
    // var trip = el.trip;
    var order = "<td>" + el.order_no + "</td>";
    var return_status = "<td>" + el.return_status + "</td>";
    var return_no = "<td>"+ el.return_no + "</td>";
    var return_amount = "<td>" + el.return_amount + "</td>";
    if (el.return_address) {
      var return_city = "<td>" + el.return_address.city + "</td>";
      const addressline = el.return_address.address_line1
      const contact = el.return_address.address_contact_number
      const shop_name = el.shop_name
      var return_address = "<td>" + shop_name + ', ' + addressline + "("+ contact + ")</td>";
    } else {
      var return_city = "-";
      var return_address = "-";
    }
    
    // var shipment_weight = "<td>" + el.shipment_weight + "</td>";
    var created_at = "<td>" + el.created_at + "</td>";
    if(el.selected){
      var select = "<td><input type='checkbox' class='return_checkbox' value='"+el.return_no+"' checked></td>";
    $("tbody#returns_data").prepend("<tr class=" + row + ">" + select + return_no + return_amount + return_status + return_city + created_at + order +  return_address  +"</tr>");
    }
    else{
      select = "<td><input type='checkbox' class='return_checkbox' value='"+el.return_no+"'></td>";
    $("tbody#returns_data").append("<tr class=" + row + ">" + select + return_no + return_amount + return_status + return_city + created_at + order +  return_address  +"</tr>");
    }
  });
  displaySelectedCount();
  if (GetTripStatus() == 'COMPLETED'|| (GetTripStatus() == 'STARTED' && trip_status == 'STARTED') || GetTripStatus() == 'CLOSED'){
    $(".return_checkbox").prop("checked", true);
    $(".return_checkbox").attr("disabled", true);
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
  $(document).on('click', '.return_checkbox', function() {
    if ($(this).is(':checked')) {
        return_page_data[$(this).val()].selected=true
    } else {
        return_page_data[$(this).val()].selected=false
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

function GetTripSourceShopType(){
    var source_shop = $('select#id_source_shop  option:selected').text();
    const arr = source_shop.split("-")
    var source_shop_type = arr.at(-2);
    if(source_shop_type == " Dispatch Center ") {
        return "dc"
    }
    else{
        return "sp"
    }
}


function CallAPI(){
  if (GetTripStatus() != ('READY')){
    GetResultByTripID();
  }
  else{
    GetResultByTripAndSellerShop();
  }
}

const CallReturnAPI = () => {
  if (GetTripStatus() != ('READY')){
    GetReturnResultByTripID();
  }
  else{
    GetReturnResultByTripAndSellerShop();
  }
}

$('#show_invoices').click((event) => {
  // this.css("background-color","#417690")
  event.target.style['background-color'] = "#417690"
  $('#show_returns').css("background-color","#79aec8")
  $('#returns_table').css('display', "none")
  $('#invoices_table').css('display', "block")
})

$('#show_returns').click((event) => {
  // this.css("background-color","#417690")
  event.target.style['background-color'] = "#417690"
  $('#show_invoices').css("background-color","#79aec8")
  $('#invoices_table').css('display', "none")
  $('#returns_table').css('display', "block")
})