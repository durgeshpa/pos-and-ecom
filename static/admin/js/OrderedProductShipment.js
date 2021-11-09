(function($) {
    'use strict';

    // IE doesn't accept periods or dashes in the window name, but the element IDs
    // we use to generate popup window names may contain them, therefore we map them
    // to allowed characters in a reversible way so that we can locate the correct
    // element when the popup window is dismissed.
    function id_to_windowname(text) {
        text = text.replace(/\./g, '__dot__');
        text = text.replace(/\-/g, '__dash__');
        return text;
    }

    function windowname_to_id(text) {
        text = text.replace(/__dot__/g, '.');
        text = text.replace(/__dash__/g, '-');
        return text;
    }

    function showAdminPopup(triggeringLink, name_regexp, add_popup) {
        var name = triggeringLink.id.replace(name_regexp, '');
        name = id_to_windowname(name);
        var href = triggeringLink.href;
        if (add_popup) {
            if (href.indexOf('?') === -1) {
                href += '?_popup=1';
            } else {
                href += '&_popup=1';
            }
        }
        var win = window.open(href, name, 'height=500,width=800,resizable=yes,scrollbars=yes');
        win.focus();
        return false;
    }

    function showRelatedObjectPopup(triggeringLink) {
        return showAdminPopup(triggeringLink, /^(change|add|delete)_/, false);
    }

    function dismissAddRelatedObjectPopup(win, newId, newRepr) {
      var name = windowname_to_id(win.name);
      var elem = document.getElementById(name);
      $(elem).text(newRepr);
      $(elem).attr("href", win.location.origin+"/admin/retailer_to_sp/shipmentrescheduling/"+newId+"/change/");
      win.close();
    }


    // Global for testing purposes
    window.id_to_windowname = id_to_windowname;
    window.windowname_to_id = windowname_to_id;

    window.dismissRelatedLookupPopup = dismissRelatedLookupPopup;
    window.showRelatedObjectPopup = showRelatedObjectPopup;
    window.dismissAddRelatedObjectPopup = dismissAddRelatedObjectPopup;

    // Kept for backward compatibility
    window.showAddAnotherPopup = showRelatedObjectPopup;
    window.dismissAddAnotherPopup = dismissAddRelatedObjectPopup;

    $(document).ready(function() {

        $('body').on('click', '.related-widget-wrapper-link-custom', function(e) {
            e.preventDefault();
            if (this.href) {
                var event = $.Event('django:show-related', {href: this.href});
                $(this).trigger(event);
                if (!event.isDefaultPrevented()) {
                    showRelatedObjectPopup(this);
                }
            }
        });


    $("select[id$='rescheduling_reason']").change(function() {
      $('option:selected', $(this)).each(function() {
            swal({
              closeOnClickOutside: false,
              closeOnEsc: false,
              icon: "warning",
              text: "Are you sure to Reschedule the Shipment?",
              dangerMode: false,
              buttons: ['No', 'Yes'],
            })
            .then(willDelete => {
              if (willDelete) {
                $("input[id$='returned_qty']").val(0);
                $("input[id$='returned_qty']").prop("readonly", true);
                $("input[id$='damaged_qty']").val(0);
                $("input[id$='damaged_qty']").prop("readonly", true);
                $("select[id='id_return_reason']").val('');
                $("select[id='id_return_reason']").attr("disabled", true);
                $("select[id$='not_attempt_reason']").val('');
                $("select[id$='not_attempt_reason']").attr("disabled", true);
              } else {
                $("select[id$='rescheduling_reason']").val('');
                $("input[id$='returned_qty']").prop("readonly", false);
                $("input[id$='damaged_qty']").prop("readonly", false);
                $("select[id$='id_return_reason']").attr("disabled", false);
                $("select[id$='not_attempt_reason']").attr("disabled", false);

              }
            });
      });

  });


    $("select[id$='not_attempt_reason']").change(function() {
      $('option:selected', $(this)).each(function() {
            swal({
              closeOnClickOutside: false,
              closeOnEsc: false,
              icon: "warning",
              text: "Are you sure to not attempt the Shipment?",
              dangerMode: false,
              buttons: ['No', 'Yes'],
            })
            .then(willDelete => {
              if (willDelete) {
                $("input[id$='returned_qty']").val(0);
                $("input[id$='returned_qty']").prop("readonly", true);
                $("input[id$='damaged_qty']").val(0);
                $("input[id$='damaged_qty']").prop("readonly", true);
                $("select[id='id_return_reason']").val('');
                $("select[id='id_return_reason']").attr("disabled", true);
                $("select[id$='rescheduling_reason']").val('');
                $("select[id$='rescheduling_reason']").attr("disabled", true);
              } else {
                $("select[id$='not_attempt_reason']").val('');
                $("input[id$='returned_qty']").prop("readonly", false);
                $("input[id$='damaged_qty']").prop("readonly", false);
                $("select[id='id_return_reason']").attr("disabled", false);
                $("select[id$='rescheduling_reason']").attr("disabled", false);

              }
            });
      });

  });

    });

})(django.jQuery);
