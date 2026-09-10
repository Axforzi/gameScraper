const steamOfertas = document.querySelector('.ofertas-steam');
const gogOfertas = document.querySelector('.ofertas-gog');
const egsOfertas = document.querySelector('.ofertas-egs');

const ofertaTemplate = document.querySelector('.oferta-template').content;
const ofertasFragment = document.createDocumentFragment();

// Slightly above the server-side 60s crawl budget: a slow-but-alive crawl
// still renders, while a dead one shows an error instead of a forever spinner.
const REQUEST_TIMEOUT_MS = 65000;
const ERROR_MESSAGE = 'Error al cargar ofertas';

const showError = (container, message = ERROR_MESSAGE) => {
    container.textContent = '';
    const errorBox = document.createElement('h2');
    errorBox.className = 'text-white fst-italic mb-3';
    errorBox.textContent = message;
    container.appendChild(errorBox);
};

const renderStore = (container, button, offers) => {
    offers.forEach(element => {
        const clone = ofertaTemplate.cloneNode(true);
        const nombreEl = clone.querySelector('.nombre');

        // OBTENER PORCENTAJE
        const porcentaje = 100 - ((element.descuento * 100) / element.precio);

        // ESCRIBIR NOMBRE Y PORCENTAJE COMO TEXTO (sin innerHTML con datos)
        const descuentoBadge = document.createElement('span');
        descuentoBadge.className = 'descuento';
        descuentoBadge.textContent = ` -${porcentaje.toFixed(2)}% `;
        nombreEl.textContent = element.nombre;
        nombreEl.prepend(descuentoBadge);

        clone.querySelector('img').src = element.img;
        clone.querySelector('a').href = element.link;
        clone.querySelector('.precio').innerText = `${element.precio}$`;
        clone.querySelector('.final').innerText = `${element.descuento}$`;

        ofertasFragment.appendChild(clone);
    });

    container.innerHTML = '';
    container.appendChild(ofertasFragment);
    button.classList.toggle('d-none');
};

const getOfertas = async () => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    let json;
    try {
        const res = await fetch('/ofertas', {
            method: 'POST',
            headers: {
                'content-type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            signal: controller.signal
        });

        // Check the HTTP status BEFORE parsing, so a non-JSON error body
        // (HTML error page, 502/504) never becomes an unhandled rejection.
        if (!res.ok) {
            let message = ERROR_MESSAGE;
            try {
                const body = await res.json();
                message = body.error || message;
            } catch {
                // non-JSON body: keep the default message
            }
            showError(steamOfertas, message);
            showError(gogOfertas, message);
            showError(egsOfertas, message);
            return;
        }

        json = await res.json();
    } catch (err) {
        // transport failure, non-JSON body, or abort: never leave the spinner
        showError(steamOfertas);
        showError(gogOfertas);
        showError(egsOfertas);
        console.error(err);
        return;
    } finally {
        clearTimeout(timeoutId);
    }

    // Keep the existing per-store rendering structure.
    try {
        renderStore(steamOfertas, document.querySelector('.btn-steam'), json.steam);
    } catch (err) {
        steamOfertas.innerHTML = '<h2 style="color: white; font-style: italic; margin-bottom: 20px;"> ---- No hay ofertas ---- </h2>';
        console.log(err);
    }

    try {
        renderStore(egsOfertas, document.querySelector('.btn-egs'), json.egs);
    } catch (err) {
        egsOfertas.innerHTML = '<h2 style="color: white; font-style: italic; margin-bottom: 20px;"> ---- No hay ofertas ---- </h2>';
        console.log(err);
    }

    try {
        renderStore(gogOfertas, document.querySelector('.btn-gog'), json.gog);
    } catch (err) {
        gogOfertas.innerHTML = '<h2 style="color: white; font-style: italic; margin-bottom: 20px;"> ---- No hay ofertas ---- </h2>';
        console.log(err);
    }
};

getOfertas();