$( document ).ready(function() {
var q = {};
location.href.split('?')[1].split('&').forEach(function(i){
    q[i.split('=')[0]]=i.split('=')[1];
});
if ("visible" in q)
    $("#id_visible").val(q.visible)
});