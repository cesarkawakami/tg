(function($) {
    $(function() {
        $.history.init(function(hash) {
            if (hash)
                $("form[name=problem] [name=problem]").val(hash);
        });
        var channelUpdater = new ChannelUpdater(
            "/contestant/channel/runs",
            "/contestant/runs",
            $("#runs")
        );
        channelUpdater.poll();
    });
})(jQuery);
