const steamOfertas = document.querySelector('.ofertas-steam');
const gogOfertas = document.querySelector('.ofertas-gog');
const egsOfertas = document.querySelector('.ofertas-egs');

const ofertaTemplate = document.querySelector('.oferta-template').content;
const ofertasFragment = document.createDocumentFragment();

const getOfertas = async () => {
    const res = await fetch('/ofertas', {
        method: 'POST',
        headers: {'content-type': 'application/json'}
    });
    const json = await res.json();

    if (!res.ok) {
        const errorBox = document.createElement('h2');
        errorBox.style.color = 'white';
        errorBox.style.fontStyle = 'italic';
        errorBox.style.marginBottom = '20px';
        errorBox.textContent = json.error || 'Error al consultar ofertas';
        const steamContainer = document.querySelector('.ofertas-steam');
        steamContainer.textContent = '';
        steamContainer.appendChild(errorBox);
        return;
    }
    
    try {
        json.steam.forEach(element => {
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

            ofertasFragment.appendChild(clone)
        });
        steamOfertas.innerHTML = '';
        steamOfertas.appendChild(ofertasFragment);
        document.querySelector('.btn-steam').classList.toggle('d-none');   
    } catch (err) {
        steamOfertas.innerHTML = '<h2 style="color: white; font-style: italic; margin-bottom: 20px;"> ---- No hay ofertas ---- </h2>';
        console.log(err)
    }

    try {
        json.egs.forEach(element => {
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

            ofertasFragment.appendChild(clone)
        });
        egsOfertas.innerHTML = '';
        egsOfertas.appendChild(ofertasFragment);
        document.querySelector('.btn-egs').classList.toggle('d-none');
    } catch (err) {
        egsOfertas.innerHTML = '<h2 style="color: white; font-style: italic; margin-bottom: 20px;"> ---- No hay ofertas ---- </h2>';
        console.log(err)
    }

    try {
        json.gog.forEach(element => {
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

            ofertasFragment.appendChild(clone)
        });
        gogOfertas.innerHTML = '';
        gogOfertas.appendChild(ofertasFragment);
        document.querySelector('.btn-gog').classList.toggle('d-none');   
    } catch (err) {
        gogOfertas.innerHTML = '<h2 style="color: white; font-style: italic; margin-bottom: 20px;"> ---- No hay ofertas ---- </h2>';
        console.log(err)
    }
}

getOfertas();