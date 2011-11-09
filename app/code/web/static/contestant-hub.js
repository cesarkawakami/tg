(function($) {
    $.history.init(function(hash) {
        $("form[name=problem] [name=problem]").val(hash);
    });
})(jQuery);
