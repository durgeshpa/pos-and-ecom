(function($) {
    $(document).on('change', '.admin-autocomplete', function(index){
        var abc = $(this).closest(".select2-hidden-accessible").attr("id");
        console.log($("#"+abc).val());
        //alert($(index).val());
    });
    $(document).on('formset:added', function(event, $row, formsetName) {
        alert(formsetName);
        // if (formsetName == 'author_set') {
        //     // Do something
        // }
    });

    $(document).on('formset:removed', function(event, $row, formsetName) {
        // Row removed
    });
})(django.jQuery);