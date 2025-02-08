var all_textareas = document.getElementsByTagName('textarea');
for (var i = 0; i < all_textareas.length; i++) {
    all_textareas[i].setAttribute('style', 'height:' + (all_textareas[i].scrollHeight) + 'px;overflow-y:hidden;');
    all_textareas[i].addEventListener("input", ChangeTextAreaOnInput, false);
}
function ChangeTextAreaOnInput() {
    rebuildTextArea(this);
}
function rebuildTextArea(textArea){
    textArea.style.height = 'auto';
    textArea.style.height = (textArea.scrollHeight) + 'px';
}