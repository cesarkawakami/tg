(function($) {
    goToByScroll = function (element) {
        $('html, body').animate({scrollTop: element.offset().top}, "fast");
    }

    $(function() {
        $("body").css("padding-top", 0);

        $("form[name=main]").submit(function(evt) {
            evt.preventDefault();
            $("form[name=main] input[type=submit]").val("Running...").attr("disabled", "");
            // $("#result_value").text("running...");
            var form = $(this),
                url = form.attr("action");
            $.post(url, form.serialize(), function(data) {
                $("#result_value").text(data);
                $("form[name=main] input[type=submit]").val("Run").removeAttr("disabled");
                goToByScroll($("#result"));
            }, "text");
        });

        $("form[name=main] [name=source]").val("#include <cstdio>\n\nint main() {\n    for (int i = 0; i < 50; ++i)\n        printf(\"Hello, world! %d\\n\", i);\n    return 0;\n}");
    });
})(jQuery);
