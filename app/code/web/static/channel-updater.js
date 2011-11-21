function ChannelUpdater(pollUrl, getUrl, element, oneOnly) {
    this.pollUrl = pollUrl;
    this.getUrl = getUrl;
    this.element = element;
    this._hash = "zzzzz";
    this.oneOnly = typeof(oneOnly) != "undefined" ? oneOnly : false;
}

ChannelUpdater.prototype = {
    poll: function() {
        $.post(
            this.pollUrl,
            {
                hash: this._hash,
                _xsrf: Util.getCookie("_xsrf"),
            },
            $.proxy(function(data) {
                this._hash = data["hash"];
                this.update();
                if (!oneOnly)
                    setTimeout($.proxy(this, "poll"), 0);
            }, this),
            "json"
        );
    },

    update: function() {
        $.get(this.getUrl, $.proxy(function(data) {
            this.element.html(data);
        }, this), "html");
    },
};
