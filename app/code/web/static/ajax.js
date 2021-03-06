Util = {
    getCookie: function(name) {
        var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
        return r ? r[1] : undefined;
    },
};

(function($) {
    Ajax = (function() {
        return {
            init: function() {
                $("form[data-ajaxify]").live("submit", function(evt) {
                    evt.preventDefault();
                    var form = $(this),
                        url = form.attr("action");
                    $.post(url, form.serialize(), null, "script");
                });

                $("a[data-ajaxify]").live("click", function(evt) {
                    evt.preventDefault();
                    $.post($(this).attr("href"), {_xsrf: Util.getCookie("_xsrf")}, null, "script");
                });

                $("a[data-formsubmit]").live("click", function(evt) {
                    evt.preventDefault();
                    $(this).parents("form").submit();
                });
            },

            reload: function() {
                window.location.reload(true);
            },
        };
    })();


    $(Ajax.init);
})(jQuery);
