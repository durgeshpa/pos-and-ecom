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

function ApprovePayment(id) {
  /*$.ajax({
      url: ,
      data: {
          'is_payment_approved': true,
      },
      complete: function(){
        $("#loading").hide();
      },
      success: function(data) {
        CheckResponse(data);
      }
  });*/
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


//var shipment_payment_id;
function CreateResponseTable(data){
  var trip_id = $('#id_trip_id').val();
  var trip_status = data['response_data'][0]['trip_status'];

  for (var i = 0; i < data['response_data'].length; i++) {
      var row = "row2";
      if (i % 2 === 0) {
          var row = "row1";
      }
      var data1 = data['response_data'][i];
      var total_amount = data['response_data'][i]['cash_to_be_collected'];
      var shipment_payment_id = data1['shipment_payment']['shipment_payment_id'];
      var shipment_payment = "shipment_payment" + shipment_payment_id;
      var pk = data['response_data'][i]['pk'];
      var is_payment_approved = data['response_data'][i]['is_payment_approved'];
      var trip = data['response_data'][i]['trip'];
      var order = "<td>" + data['response_data'][i]['order'] + "</td>";
      var shipment_status = "<td><a href='/admin/retailer_to_sp/orderedproduct/"+pk+"/change/' target='_blank'>" + data['response_data'][i]['shipment_status'] + "</a></td>";
      var payment_approval_status = "<td>" + data['response_data'][i]['payment_approval_status'] + "</td>";
      var online_payment_approval_status = "<td>" + data['response_data'][i]['online_payment_approval_status'] + "</td>";
      //var invoice_no = "<td><a href='/admin/retailer_to_sp/cart/commercial/"+pk+"/shipment-details/' target='_blank'>"+ data['response_data'][i]['invoice_no'] + "</a></td>";
      var invoice_no = "<td><a href='/admin/payments/shipmentdata/"+pk+"/change/' target='_blank'>"+ data['response_data'][i]['invoice_no'] + "</a></td>";
      var discounted_credit_note_pk = data['response_data'][i]['discounted_credit_note_pk'];
      var discounted_credit_note = "<td><a href='/admin/retailer_to_sp/note/"+discounted_credit_note_pk+"/change/' target='_blank'>"+ data['response_data'][i]['discounted_credit_note'] + "</a></td>";

      var invoice_amount = "<td>" + data['response_data'][i]['invoice_amount'] + "</td>";
      var cash_to_be_collected = "<td>" + data['response_data'][i]['cash_to_be_collected'] + "</td>";
      var paid_amount_shipment = "<td>" + data['response_data'][i]['paid_amount_shipment'] + "</td>";
/*      var cash_payment = "<td><form class='"+ shipment_payment +"' action=''><input type='number' placeholder='0.0' step='0.01' min='0' name='cash_amount' value='"+ data1['shipment_payment']['cash_payment_amount'] +"'></form></td>";
      var online_payment_mode = "<td><form class='"+ shipment_payment +"' action=''><select name='payment_mode' id='mode_"+ shipment_payment_id +"'><option value=''>Select</option>"+
      "<option value='neft'>NEFT</option><option value='upi'>UPI</option><option value='rtgs'>RTGS</option><option value='imps'>IMPS</option>"+
      "</select></form></td>";
      var online_payment = "<td><form class='"+ shipment_payment +"' action=''><input type='number' placeholder='0.0' step='0.01' min='0' name='online_amount' value='"+ data1['shipment_payment']['online_payment_amount'] +"'></form></td>";
      var reference_no = "<td><form class='"+ shipment_payment +"' action=''><input type='text' name='reference_no' value='"+ data1['shipment_payment']['reference_no'] +"'></form></td>";
      var description = "<td><form class='"+ shipment_payment +"' action=''><input type='text' name='description' value='"+ data1['shipment_payment']['description'] +"'></form></td>";*/
      var invoice_city = "<td>" + data['response_data'][i]['invoice_city'] + "</td>";
      var shipment_address = "<td>" + data['response_data'][i]['shipment_address'] + "</td>";
      var created_at = "<td>" + data['response_data'][i]['created_at'] + "</td>";
      //var submit_payment_button = "<td><form class='"+ shipment_payment +"' action=''><button class='shipment-payments-submit' type='button' data-id='"+ shipment_payment_id +"' data-total='"+ total_amount +"'>Submit!</button></form></td>";

      var append_data = "<tr class="+ row +"><td class='original'></td>" + invoice_no + invoice_amount + cash_to_be_collected + paid_amount_shipment + shipment_status +
      payment_approval_status + online_payment_approval_status +invoice_city + created_at + order + shipment_address + discounted_credit_note + "</tr>";

      /*var append_data = "<tr class="+ row +"><td class='original'></td>" + invoice_no + invoice_amount + cash_to_be_collected + cash_payment
      + online_payment_mode + online_payment + reference_no + description +shipment_status +
      invoice_city + created_at + order + shipment_address + submit_payment_button +"</tr>"*/

      $("tbody#data").append(append_data);
      /*var mode = "mode_"+ shipment_payment_id;
      var mode_value = data1['shipment_payment']['payment_mode'];
      if (mode_value != "")
      $('#'+ mode +' option[value='+ mode_value +']').attr("selected", "selected");*/
  }
/*      var submit_payment_button = "<button class='shipment-payments-submit' type='button'>Submit!</button>"*/
      //$("tbody#data").append(submit_payment_button);



      $('.shipment-payments-submit').on('click',  function(event) {
          //event.preventDefault();
          var id = $(this).attr('data-id');
          var total = $(this).attr('data-total');
          update_shipment_payment_information(id, total);//('{{ shipment_payment.id | escapejs }}');

      });

/*      if (trip_status=="CLOSED" || trip_status=="TRANSFERRED"){
        $("input").prop('disabled', true);
        $("button.shipment-payments-submit").prop('disabled', true);
        $("select").prop('disabled', true);
      }*/
}

function submit_update_data(shipment_payment_id)
{
    console.log(formData);
    /*alert("test");*/
    $.ajax({
        method: 'PATCH',
        url: '/payments/api/v1/shipment-payment/'+shipment_payment_id+'/',
        async: false,
        contentType: "application/json",
        data : JSON.stringify(formData),
        success: function(data){
            console.log(data);
            alert('Successfully Updated');
            formData = {};
            location.reload();

        },
        error: function(xhr, desc, err){
            console.log("error===");
            console.log(xhr.responseText);
            alert(xhr.responseText);

            formData = {};
        }
    });
}


function validate_form_js(this_form)
{
    /* Function to validate form and highlight error field */

    var serialize_array = $(this_form).serializeArray();

    var error_count = 0;

    var form_data = {};

    $.map(serialize_array, function(n, i){
        if(n['value'].trim())
        {
            form_data[n['name']] = n['value'];
        }
        else
        {
            error_count+=1;
            this_form[n['name']].classList.add("validate_highlight");
        }
    });

    response = {
        'error_count':error_count,
        'form_data':form_data
    }

    return response;
}

formData = {};
error_counter = 0;

function update_shipment_payment_information(shipment_payment_id, total)
{
    /* Function to update shipment payment */
    var _class = "shipment_payment"+shipment_payment_id;
    var formarray = $("."+_class).serializeArray();
    //var formarray = $(".shipment_payment_info").serializeArray();

    for(var i=0; i<formarray.length;i++)
    {
        formData[formarray[i].name]=formarray[i].value;
    }

    if (formData["cash_amount"] == "")
    {
      alert("Please fill cash amount!");
      return False;
    }

    if (formData["payment_mode"]!=""){
     if (formData["online_amount"]==""){
      alert("Please fill online amount!");
      return False;
     }
     if (formData["reference_no"]==""){
      alert("Please fill reference number for online payment!");
      return False;
     }
    }

/*    if (parseFloat(formData["cash_amount"]) + parseFloat(formData["online_amount"])< parseFloat(total)){
      alert("Sum of cash amount, online amount should not be less than amount to be collected!");
      return false;
    }*/

    if (formData["payment_mode"]==""){
      //formData["payment_mode"]="none";
      formData["online_amount"]=0.0;
      formData["reference_no"]="null";
    }
    // submit update data
    submit_update_data(shipment_payment_id);

    /*var cash_payment = {};
    cash_payment['paid_amount'] = formData['cash_payment'];
    formData['cash_payment'] = cash_payment; */
    //submit_update_data(shipment_payment_id);
}

function CallAPI(){
    GetResultByTripID();
}


})(django.jQuery);
