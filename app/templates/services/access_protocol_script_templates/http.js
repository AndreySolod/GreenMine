function waitForServiceSocket(){
    if(typeof serviceSocket !== "undefined"){
        serviceSocket.on("take screenshot received", function(data) {
        $.notify(`{{ _('User __username__ request to take screenshot on protocol "__proto_name__"') }}`.replace("__username__", data.by_user).replace("__proto_name__", data.proto), "info", {
            clickToHide: true,
            autoHide: true,
            autoHideDelay: 5000,
            globalPosition: 'top right'
        });
        let div_data = null
        if(data.proto === 'http') {
            div_data = document.getElementById('screenshot_http');
            screenshot_title = document.getElementById('screenshot-http-title');
        }
        else if(data.proto === 'https') {
            div_data = document.getElementById('screenshot_https');
            screenshot_title = document.getElementById('screenshot-https-title');
        };
        for (let i = 4; i < div_data.childNodes.length + 1;i++){
            div_data.removeChild(div_data.childNodes[4]);
        };
        screenshot_title.innerHTML = '';
        let spinner = document.createElement("div");
        setMultipleAttributes(spinner, {"class": "spinner-border text-primary text-center", "role": "status"});
        let child_span = document.createElement("span");
        child_span.setAttribute("class", "visually-hidden");
        child_span.innerHTML = "{{ _('Loading...') }}";
        let over_div = document.createElement('div');
        setMultipleAttributes(over_div, {'class': 'd-flex justify-content-center'});
        spinner.appendChild(child_span);
        over_div.appendChild(spinner);
        div_data.appendChild(over_div);
    });
    serviceSocket.on("screenshot taked", function(data) {
        if(data.address !== null) {
            new_screenshot = document.createElement('img');
            setMultipleAttributes(new_screenshot, {'src': data.address, 'onerror': '{{ _("Cannot load a screenshot") }}'});
            let div_data = document.getElementById('screenshot_' + data.proto);
            div_data.removeChild(div_data.lastChild);
            div_data.appendChild(new_screenshot);
            document.getElementById('screenshot-' + data.proto + '-title').innerHTML = data.screenshot_title;
        }
        else {
            let h6_placeholder = document.createElement('h6');
            h6_placeholder.innerHTML = "{{ pgettext('man', '(Missing)') }}";
            h6_placeholder.setAttribute('class', 'text-muted text-center');
            let div_data = document.getElementById("screenshot_" + data.proto);
            div_data.removeChild(div_data.lastChild);
            div_data.appendChild(h6_placeholder);
            document.getElementById('screenshot-' + data.proto + '-title').innerHTML = data.screenshot_title;
        };
    });

    document.getElementById('http-take-screenshot-button').addEventListener('click', function(){
        serviceSocket.emit("take screenshot", {"proto": 'http'});
    });

    document.getElementById('https-take-screenshot-button').addEventListener('click', function() {
        serviceSocket.emit("take screenshot", {"proto": 'https'});
    });

    } else{
        setTimeout(waitForServiceSocket, 1000);
    }
};
waitForServiceSocket();