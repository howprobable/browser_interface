(() => {
    function getVisibleInnerText(element) {
        let result = [];
        if(!element) return result; 
        if (element.nodeType === Node.TEXT_NODE && isVisible(element.parentNode)) {
            content = element.nodeValue.trim(); 
            if(content != ""){
                rect = getRect(element)
                result.push({rect: [rect.x,rect.y, rect.height, rect.width], text: content});
            } 
        } else if (element.nodeType === Node.ELEMENT_NODE && isVisible(element)) {
            for (let child of element.childNodes) {
                content = getVisibleInnerText(child)
                for(let cont of content)
                    result.push(cont);
            }
        }
        return result;
    }

    function isVisible(elem) {
        const style = window.getComputedStyle(elem);
        return style.display !== 'none' && style.visibility !== 'hidden';
    }

    function getRect(elem){
        let range = document.createRange();
        range.selectNode(elem);
        return range.getBoundingClientRect();
    }
    return getVisibleInnerText(document.body)})()