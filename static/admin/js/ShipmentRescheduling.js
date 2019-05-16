(function($) {
  $(document).ready(function() {
    flatpickr("input[id$='rescheduling_date']", {
    dateFormat: "Y-m-d",
    minDate: new Date().fp_incr(1), // tommorow
    maxDate: new Date().fp_incr(3) // 3 days from now
  });
});
})(django.jQuery);
