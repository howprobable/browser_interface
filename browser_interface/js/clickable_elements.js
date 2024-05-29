Array.from(
    document.querySelectorAll("a, button, input[type='button'], input[type='submit'], [onclick], [tabindex]:not([tabindex='-1']), [aria-label]")
)
    .filter(element => (
        element.innerText && element.innerText.trim().length > 0) 
    || (element.title && element.title.trim().length > 0 ) 
    || (element.getAttribute('aria-label') && element.getAttribute('aria-label').trim().length > 0))
    .filter(element => element.click != undefined)
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
            text: (element.innerText ?? "").trim(),
            title: (element.title ?? "").trim(), 
            ariaLabel: (element.getAttribute('aria-label') ?? "").trim(), 
            rect: [
                element.getBoundingClientRect().x,
                element.getBoundingClientRect().y, 
                element.getBoundingClientRect().height, 
                element.getBoundingClientRect().width
            ],
        }
    })