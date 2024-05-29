Array.from(document.querySelectorAll("input[type='text'], input[type='password'], textarea, [contenteditable='true']"))
    .filter(element => (
        element.value && element.value.trim().length > 0) 
    || (element.placeholder && element.placeholder.trim().length > 0) 
    || (element.title && element.title.trim().length > 0) 
    || (element.getAttribute('aria-label') && element.getAttribute('aria-label').trim().length > 0))
    .filter(element => element.type !== 'hidden' && element.offsetHeight > 0)
    .map(element => {
        if (!element.id) {
            element.id = crypto.randomUUID().substr(0,8);
        }

        const allSameIdElements = Array.from(document.querySelectorAll('#' + CSS.escape(element.id)));
        const id_nr = allSameIdElements.findIndex(el => el === element); 

        return {
            tag: element.tagName,
            id: element.id,
            id_nr: id_nr,
            text: (element.value ?? "").trim(),
            title: (element.title ?? "").trim(),
            ariaLabel: (element.getAttribute('aria-label') ?? "").trim(),
            placeholder: (element.placeholder ?? "").trim(),
            rect: [
                element.getBoundingClientRect().x,
                element.getBoundingClientRect().y, 
                element.getBoundingClientRect().height, 
                element.getBoundingClientRect().width
            ],
        }
    })