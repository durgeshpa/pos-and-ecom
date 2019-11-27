$(document).ready(function(){

  //$('select#id_order').select2();

    $("select#id_order").change(function(){
      $("#orderedproductmapping_set-group").html('Loading! Please wait...');
       var selectedOrder= $(this).children("option:selected").val();
       var host = location.protocol + '//' + location.hostname + (location.port ? ':' + location.port : '')+'/';
       var url = host + 'admin/retailer_to_gram/orderedproduct/ajax/load-ordered-products-mapping/?order_id=' + selectedOrder;
       location.href=url;

      });
});
