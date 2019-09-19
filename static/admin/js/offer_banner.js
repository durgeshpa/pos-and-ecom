(function($) {
  $(document).ready(function() {
    $('#id_offer_banner_type').on('change',function(){
    if($(this).val()=== "brand"){
     $(".form-row.field-brand").show()
     $(".form-row.field-sub_brand").hide()
     $(".form-row.field-category").hide()
     $(".form-row.field-sub_category").hide()
     $(".form-row.field-products").hide()
    }
    if($(this).val()=== "subbrand"){
     $(".form-row.field-brand").hide()
     $(".form-row.field-sub_brand").show()
     $(".form-row.field-category").hide()
     $(".form-row.field-sub_category").hide()
     $(".form-row.field-products").hide()
    }
    if($(this).val()=== "category"){
     $(".form-row.field-brand").hide()
     $(".form-row.field-sub_brand").hide()
     $(".form-row.field-category").show()
     $(".form-row.field-sub_category").hide()
     $(".form-row.field-products").hide()
    }
    if($(this).val()=== "subcategory"){
     $(".form-row.field-brand").hide()
     $(".form-row.field-sub_brand").hide()
     $(".form-row.field-category").hide()
     $(".form-row.field-sub_category").show()
     $(".form-row.field-products").hide()
    }
    if($(this).val()=== "product"){
      $(".form-row.field-brand").hide()
      $(".form-row.field-sub_brand").hide()
      $(".form-row.field-category").hide()
      $(".form-row.field-sub_category").hide()
      $(".form-row.field-products").show()
    }
    if($(this).val()=== "offer"){
      $(".form-row.field-brand").show()
      $(".form-row.field-sub_brand").show()
      $(".form-row.field-category").show()
      $(".form-row.field-sub_category").show()
      $(".form-row.field-products").show()
    }
    if(!$(this).val()){
      $(".form-row.field-brand").hide()
      $(".form-row.field-sub_brand").hide()
      $(".form-row.field-category").hide()
      $(".form-row.field-sub_category").hide()
      $(".form-row.field-products").hide()
    }
});
$(document).ready(function() {
  if(!$('#id_offer_banner_type').val()){
  $(".form-row.field-brand").hide()
  $(".form-row.field-sub_brand").hide()
  $(".form-row.field-category").hide()
  $(".form-row.field-sub_category").hide()
  $(".form-row.field-products").hide()
}
if($('#id_offer_banner_type').val()=== "brand"){
 $(".form-row.field-brand").show()
 $(".form-row.field-sub_brand").hide()
 $(".form-row.field-category").hide()
 $(".form-row.field-sub_category").hide()
 $(".form-row.field-products").hide()
}
if($('#id_offer_banner_type').val()=== "subbrand"){
 $(".form-row.field-brand").hide()
 $(".form-row.field-sub_brand").show()
 $(".form-row.field-category").hide()
 $(".form-row.field-sub_category").hide()
 $(".form-row.field-products").hide()
}
if($('#id_offer_banner_type').val()=== "category"){
 $(".form-row.field-brand").hide()
 $(".form-row.field-sub_brand").hide()
 $(".form-row.field-category").show()
 $(".form-row.field-sub_category").hide()
 $(".form-row.field-products").hide()
}
if($('#id_offer_banner_type').val()=== "subcategory"){
 $(".form-row.field-brand").hide()
 $(".form-row.field-sub_brand").hide()
 $(".form-row.field-category").hide()
 $(".form-row.field-sub_category").show()
 $(".form-row.field-products").hide()
}
if($('#id_offer_banner_type').val()=== "product"){
  $(".form-row.field-brand").hide()
  $(".form-row.field-sub_brand").hide()
  $(".form-row.field-category").hide()
  $(".form-row.field-sub_category").hide()
  $(".form-row.field-products").show()
}
});
$('#id_offer_banner_type').on('change',function(){
  $('.banner-select2').val(null).trigger('change');
});
});
})(django.jQuery);
