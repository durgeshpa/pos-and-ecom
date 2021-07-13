/* dynamic_inlines_with_sort.js */
/* Created in May 2009 by Hannes Rydén */
/* Modified in September 2011 by Alessandro Bruni */
/* Use, distribute and modify freely */

// "Add"-link html code. Defaults to Django's "+" image icon, but could use text instead.
add_link_html = '<img src="/static/admin/img/icon-addlink.svg" ' +
    'width="10" height="10" alt="Add new row" style="margin:0.5em 1em;" />';
// "Delete"-link html code. Defaults to Django's "x" image icon, but could use text instead.
delete_link_html = '<img src="/static/admin/img/icon-deletelink.svg" ' +
    'width="10" height="10" alt="Delete row" style="margin-top:0.5em" />';
position_field = 'order'; // Name of inline model field (integer) used for ordering. Defaults to "position".

var noOfItems;
jQuery(function($) {
    noOfItems= $("td.field-picked_pieces input").length
    changeExpPieces()
    changeval()
    changePickedPieces()
    updateval()
    changeDamagedPieces()
    changeMissingPieces()
    changeRejectedPieces()
    loadPickedPieces()
    loadToShip()
    removeAddAnotherButton()
    // This script is applied to all TABULAR inlines
    $('div.inline-group div.tabular').each(function() {
        table = $(this).find('table');

        // Hide initial extra row and prepare it to be used as a template for new rows
        add_template = table.find('tr.empty-form');
        add_template.addClass('add_template').hide();
	table.prepend(add_template);

	// Remove original add button
	table.find('tr.add-row').remove();

        // Hide initial deleted rows
        table.find('td.delete input:checkbox:checked').parent('td').parent('tr').addClass('deleted_row').hide();

        // "Add"-button in bottom of inline for adding new rows
        $(this).find('tr.form-row').append('<a class="add" onclick="add_row(table)">' + add_link_html + '</a>');

        $(this).find('a.add').click(function(){
            new_item = add_template.clone(true);

            create_delete_button(new_item.find('td.delete'));
            new_item.removeClass('add_template').removeClass('empty-form').show();

            $(this).parent().find('table').append(new_item);

            update_positions($(this).parent().find('table'), true);

            // Place for special code to re-enable javascript widgets after clone (e.g. an ajax-autocomplete field)
            // Fictive example: new_item.find('.autocomplete').each(function() { $(this).triggerHandler('autocomplete'); });
        }).removeAttr('href').css('cursor', 'pointer');

        // "Delete"-buttons for each row that replaces the default checkbox
        table.find('tr:not(.add_template) td.delete').each(function() {
            create_delete_button($(this));
        });

        // Drag and drop functionality - only used if a position field exists
        if (position_field != '' && table.find('td').is('.' + position_field))
        {
            // Hide "position"-field (both td:s and th:s)
            $(this).find('td.' + position_field).hide();
            td_pos_field_index = table.find('tbody tr td').index($(this).find('td.' + position_field));
            $(this).find('th:eq(' + (td_pos_field_index-1) + ')').hide();

            // Hide "original"-field and set any colspan to 1 (why show in the first case?)
            $(this).find('td.original').hide();
            $(this).find('th[colspan]').removeAttr('colspan');

            // Make table sortable using jQuery UI Sortable
            table.sortable({
                items: 'tr:has(td)',
                tolerance: 'pointer',
                axis: 'y',
                cancel: 'input,button,select,a',
                helper: 'clone',
                update: function() {
                    update_positions($(this));
                }
            });


            // Re-order <tr>:s based on the "position"-field values.
            // This is a very simple ordering which only works with correct position number sequences,
            // which the rest of this script (hopefully) guarantees.
            rows = [];
            table.find('tbody tr').each(function() {
                position = $(this).find('td.' + position_field + ' input').val();
                rows[position] = $(this);

                // Add move cursor to table row.
                // Also remove row coloring, as it confuses when using drag-and-drop for ordering
                table.find('tr:has(td)').css('cursor', 'move').removeClass('row1').removeClass('row2');
            });

            for (var i in rows) { table.append(rows[i]); } // Move <tr> to its correct position
            update_positions($(this), true);
        }
        else
            position_field = '';

	// Detach the template row
        add_template.detach();
    });
});

// Function for creating fancy delete buttons
function create_delete_button(td)
{
     // Replace checkbox with image
    td.find('input:checkbox').hide();
    td.append('<a class="delete" href="#">' + delete_link_html + '</a>');

    td.find('a.delete').click(function(){
        current_row = $(this).parent('td').parent('tr');
        table = current_row.parent().parent();
        if (current_row.is('.has_original')) // This row has already been saved once, so we must keep checkbox
        {
            $(this).prev('input').attr('checked', true);
            current_row.addClass('deleted_row').hide();
        }
        else // This row has never been saved so we can just remove the element completely
        {
            current_row.remove();
        }

        update_positions(table, true);
    }).removeAttr('href').css('cursor', 'pointer');
}

// Updates "position"-field values based on row order in table
function update_positions(table, update_ids)
{
    even = true;
    num_rows = 0
    position = 0;

    // Set correct position: Filter through all trs, excluding first th tr and last hidden template tr
    table.find('tbody tr:not(.add_template):not(.deleted_row)').each(function() {
        if (position_field != '')
        {
            // Update position field
            $(this).find('td.' + position_field + ' input').val(position + 1);
            position++;
        }
        else
        {
            // Update row coloring
            $(this).removeClass('row1 row2');
            if (even)
            {
                $(this).addClass('row1');
                even = false;
            }
            else
            {
                $(this).addClass('row2');
                even = true;
            }
        }
    });

    table.find('tbody tr.has_original').each(function() {
        num_rows++;
    });

    table.find('tbody tr:not(.has_original):not(.add_template)').each(function() {
        if (update_ids) update_id_fields($(this), num_rows);
        num_rows++;
    });

    table.find('tbody tr.add_template').each(function() {
        if (update_ids) update_id_fields($(this), num_rows);
        num_rows++;
    });

    table.parent().parent('div.tabular').find("input[id$='TOTAL_FORMS']").val(num_rows);
}

// Updates actual id and name attributes of inputs, selects and so on.
// Required for Django validation to keep row order.
function update_id_fields(row, new_position)
{
    // Fix IDs, names etc.

    // <select ...>
    row.find('select').each(function() {
        // id=...
        old_id = $(this).attr('id').toString();
        new_id = old_id.replace(/([^ ]+\-)(?:\d+|__\w+__)(\-[^ ]+)/i, "$1" + new_position + "$2");
        $(this).attr('id', new_id);

        // name=...
        old_id = $(this).attr('name').toString();
        new_id = old_id.replace(/([^ ]+\-)(?:\d+|__\w+__)(\-[^ ]+)/i, "$1" + new_position + "$2");
        $(this).attr('name', new_id);
    });

    // <input ...>
    row.find('input').each(function() {
        // id=...
        old_id = $(this).attr('id').toString();
        new_id = old_id.replace(/([^ ]+\-)(?:\d+|__\w+__)(\-[^ ]+)/i, "$1" + new_position + "$2");
        $(this).attr('id', new_id);

        // name=...
        old_id = $(this).attr('name').toString();
        new_id = old_id.replace(/([^ ]+\-)(?:\d+|__\w+__)(\-[^ ]+)/i, "$1" + new_position + "$2");
        $(this).attr('name', new_id);
    });

    // Are there other element types...? Add here.
}

function add_row(table)
{
        var table = table,
        lastRow = table.find('tbody tr:last'),
        rowClone = lastRow.clone();
        table.find('tbody').append(rowClone);
        td = rowClone.append('<a class="delete" onclick=delete_row(table)>' + delete_link_html + '</a>')
}


function changeval(){
    $(document).ready(function(){
        xx = [0,1,2,3,4,5,6]
        $("input[name^='rt_order_product_order_product_mapping']").keyup(function(){
    for(var i=0;i<noOfItems;i++){
        var sum = 0
        for (var j=0; j<10;j++){
            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-quantity` + "]").val())
            if (isNaN(tot)){
                continue
            }
            sum +=tot
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-shipped_qty` + "]").val(sum);

        }
        }
        });
    })
}

function changePickedPieces(){
    $(document).ready(function(){
        xx = [0,1,2,3,4,5,6]
        $("input[name$='-pickup_quantity']").keyup(function(){
    for(var i=0;i<noOfItems;i++){
        var sum = 0
        for (var j=0; j<10;j++){
            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-pickup_quantity` + "]").val())
            if (isNaN(tot)){
                continue
            }
            sum +=tot
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-picked_pieces` + "]").val(sum);

        }
        }
        });
    })
}

function changeDamagedPieces(){
    $(document).ready(function(){
        xx = [0,1,2,3,4,5,6]
        $("input[name$='-damaged_qty']").keyup(function(){
    for(var i=0;i<noOfItems;i++){
        var sum = 0
        var final_sum = 0
        var additional_qty = 0
        for (var j=0; j<10;j++){
//            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-damaged_qty` + "]").val())
            var damaged_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-damaged_qty` + "]").val())
            var expired_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-expired_qty` + "]").val())
            var missing_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-missing_qty` + "]").val())
            var rejected_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-rejected_qty` + "]").val())

            var quantity = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-pickup_quantity` + "]").val())
//            if (isNaN(tot)){
//                tot = 0
//            }
            if (isNaN(damaged_qty)){
                damaged_qty = 0
            }
            if (isNaN(expired_qty)){
                expired_qty = 0
            }
            if (isNaN(missing_qty)){
                missing_qty = 0
            }
            if (isNaN(rejected_qty)){
                rejected_qty = 0
            }
            if (isNaN(quantity)){
                quantity = 0
            }
            if (isNaN(final_qty)){
                final_qty = 0
            }
            additional_qty = damaged_qty + expired_qty + missing_qty + rejected_qty
            if (additional_qty > quantity)
            {
            sum +=damaged_qty
            final_sum =quantity
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-damaged_qty` + "]").val(sum);
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-quantity` + "]").val(final_sum)
            }
            else
            {
            var final_qty = quantity -(damaged_qty + expired_qty + missing_qty + rejected_qty)
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-quantity` + "]").val(final_qty)
            sum +=damaged_qty
            final_sum +=final_qty
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-damaged_qty` + "]").val(sum);
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-shipped_qty` + "]").val(final_sum);
            }
        }
        }
        });
    })
}

function changeExpPieces(){
    $(document).ready(function(){
        xx = [0,1,2,3,4,5,6]
        $("input[name$='-expired_qty']").keyup(function(){
    for(var i=0;i<noOfItems;i++){
        var sum = 0
        var final_sum = 0
        var additional_qty = 0
        for (var j=0; j<10;j++){
//            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-expired_qty` + "]").val())
            var damaged_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-damaged_qty` + "]").val())
            var expired_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-expired_qty` + "]").val())
            var missing_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-missing_qty` + "]").val())
            var rejected_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-rejected_qty` + "]").val())
            var pickup_quantity = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-pickup_quantity` + "]").val())
//            if (isNaN(tot)){
//                tot = 0
//            }
            if (isNaN(damaged_qty)){
                damaged_qty = 0
            }
            if (isNaN(expired_qty)){
                expired_qty = 0
            }
            if (isNaN(missing_qty)){
                missing_qty = 0
            }
            if (isNaN(rejected_qty)){
                rejected_qty = 0
            }
            if (isNaN(pickup_quantity)){
                quantity = 0
            }
            if (isNaN(final_qty)){
                final_qty = 0
            }
            additional_qty = damaged_qty + expired_qty + missing_qty + rejected_qty
            if (additional_qty > pickup_quantity)
            {
            sum +=expired_qty
            final_sum =pickup_quantity
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-expired_qty` + "]").val(sum);
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-quantity` + "]").val(final_sum)
            }
            else
            {
            var final_qty = pickup_quantity -(damaged_qty + expired_qty + missing_qty + rejected_qty)
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-quantity` + "]").val(final_qty)
            sum +=expired_qty
            final_sum +=final_qty
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-expired_qty` + "]").val(sum);
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-shipped_qty` + "]").val(final_sum);
            }
        }
        }
        });
    })
}


function changeMissingPieces(){
    $(document).ready(function(){
        xx = [0,1,2,3,4,5,6]
        $("input[name$='-missing_qty']").keyup(function(){
    for(var i=0;i<noOfItems;i++){
        var sum = 0
        var final_sum = 0
        var additional_qty = 0
        for (var j=0; j<10;j++){
//            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-expired_qty` + "]").val())
            var damaged_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-damaged_qty` + "]").val())
            var expired_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-expired_qty` + "]").val())
            var missing_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-missing_qty` + "]").val())
            var rejected_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-rejected_qty` + "]").val())
            var pickup_quantity = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-pickup_quantity` + "]").val())
//            if (isNaN(tot)){
//                tot = 0
//            }
            if (isNaN(damaged_qty)){
                damaged_qty = 0
            }
            if (isNaN(expired_qty)){
                expired_qty = 0
            }

            if (isNaN(missing_qty)){
                missing_qty = 0
            }

            if (isNaN(rejected_qty)){
                rejected_qty = 0
            }
            if (isNaN(pickup_quantity)){
                pickup_quantity = 0
            }
            if (isNaN(final_qty)){
                final_qty = 0
            }
            additional_qty = damaged_qty + expired_qty + missing_qty + rejected_qty
            if (additional_qty > pickup_quantity)
            {
            sum +=missing_qty
            final_sum =pickup_quantity
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-missing_qty` + "]").val(sum);
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-quantity` + "]").val(final_sum)
            }
            else
            {
            var final_qty = pickup_quantity -(damaged_qty + expired_qty + missing_qty + rejected_qty)
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-quantity` + "]").val(final_qty)
            sum +=missing_qty
            final_sum +=final_qty
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-missing_qty` + "]").val(sum);
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-shipped_qty` + "]").val(final_sum);
            }
        }
        }
        });
    })
}

function changeRejectedPieces(){
    $(document).ready(function(){
        xx = [0,1,2,3,4,5,6]
        $("input[name$='-rejected_qty']").keyup(function(){
    for(var i=0;i<noOfItems;i++){
        var sum = 0
        var final_sum = 0
        var additional_qty = 0
        for (var j=0; j<10;j++){
//            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-expired_qty` + "]").val())
            var damaged_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-damaged_qty` + "]").val())
            var expired_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-expired_qty` + "]").val())
            var missing_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-missing_qty` + "]").val())
            var rejected_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-rejected_qty` + "]").val())
            var pickup_quantity = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-pickup_quantity` + "]").val())
//            if (isNaN(tot)){
//                tot = 0
//            }
            if (isNaN(damaged_qty)){
                damaged_qty = 0
            }
            if (isNaN(expired_qty)){
                expired_qty = 0
            }

            if (isNaN(missing_qty)){
                missing_qty = 0
            }

            if (isNaN(rejected_qty)){
                rejected_qty = 0
            }
            if (isNaN(pickup_quantity)){
                pickup_quantity = 0
            }
            if (isNaN(final_qty)){
                final_qty = 0
            }
            additional_qty = damaged_qty + expired_qty + missing_qty + rejected_qty
            if (additional_qty > pickup_quantity)
            {
            sum +=rejected_qty
            final_sum =pickup_quantity
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-rejected_qty` + "]").val(sum);
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-quantity` + "]").val(final_sum)
            }
            else
            {
            var final_qty = pickup_quantity -(damaged_qty + expired_qty + missing_qty + rejected_qty)
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-quantity` + "]").val(final_qty)
            sum +=rejected_qty
            final_sum +=final_qty
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-rejected_qty` + "]").val(sum);
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-shipped_qty` + "]").val(final_sum);
            }
        }
        }
        });
    })
}


function loadPickedPieces(){
    $(document).ready(function(){
        xx = [0,1,2,3,4,5,6]
    for(var i=0;i<noOfItems;i++){
        var sum = 0
        for (var j=0; j<10;j++){
            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-pickup_quantity` + "]").val())
            if (isNaN(tot)){
                continue
            }
            sum +=tot
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-picked_pieces` + "]").val(sum);

        }
        }
    })
}

function loadToShip(){
    $(document).ready(function(){
        xx = [0,1,2,3,4,5,6]
    for(var i=0;i<noOfItems;i++){
        var sum = 0
        for (var j=0; j<10;j++){
            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-quantity` + "]").val())
            if (isNaN(tot)){
                continue
            }
            sum +=tot
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-shipped_qty` + "]").val(sum);

        }
        }
    })
}

function updateval(){
        xx = [0,1,2,3,4,5,6]
        $("input[name^='rt_order_product_order_product_mapping']").keyup(function(){
    for(var i=0;i<noOfItems;i++){
        var sum = 0
//        var final_sum  = 0
        for (var j=0; j<10;j++){
            var damaged_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-damaged_qty` + "]").val())
            var expired_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-expired_qty` + "]").val())
            var missing_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-missing_qty` + "]").val())
            var rejected_qty = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-rejected_qty` + "]").val())
            var quantity = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-pickup_quantity` + "]").val())
            var initial_quantity = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-quantity` + "]").val())
            if (quantity != initial_quantity){
            final_sum = damaged_qty + expired_qty + missing_qty + rejected_qty
            quantity_value = quantity -(damaged_qty + expired_qty + missing_qty + rejected_qty)
            var tot = parseInt($("input[name=" + `rt_order_product_order_product_mapping-${i}-rt_ordered_product_mapping-${j}-quantity` + "]").val(quantity_value))
            }
            if (isNaN(tot)){
                continue
            }
            sum +=tot
            $("input[name=" + `rt_order_product_order_product_mapping-${i}-shipped_qty` + "]").val(sum);

        }
        }
    })
}

function removeAddAnotherButton(){
    $(document).ready(function(){
        $("input[name='_addanother']").hide()
    })
}