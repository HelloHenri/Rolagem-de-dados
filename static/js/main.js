var socket = io();
var user, room;

function getPColor(name) {
    let hash = 0;
    for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
    return `hsl(${Math.abs(hash * 137) % 360}, 85%, 65%)`;
}

function entrar() {
    user = document.getElementById('username').value;
    room = document.getElementById('room').value;
    if(user && room) {
        document.getElementById('setup').style.display = 'none';
        document.getElementById('game-ui').style.display = 'flex';
        socket.emit('join', {username: user, room: room});
    }
}

function enviar(manual, isReroll = false) {
    let input = document.getElementById('cmd');
    let val = manual || input.value;
    if(!val) return;
    socket.emit('send_command', {username: user, room: room, msg: val, is_reroll: isReroll});
    if(!manual) input.value = '';
}

function vRoll(lados) {
    const box = document.getElementById('v-box');
    const qtd = document.getElementById('v-qtd').value || 1;
    const bonus = document.getElementById('v-bonus').value || 0;
    box.classList.add('rolling');
    let c = 0;
    let anim = setInterval(() => {
        document.getElementById('v-total').innerText = Math.floor(Math.random() * (lados * qtd)) + 1;
        if(c++ > 8) {
            clearInterval(anim);
            box.classList.remove('rolling');
            enviar(`${qtd}d${lados}${bonus >= 0 ? '+' : ''}${bonus}`);
        }
    }, 50);
}

socket.on('new_roll', function(data) {
    const color = getPColor(data.user);
    if(data.user === user) {
        document.getElementById('v-total').innerText = data.repeticoes[0].total;
        document.getElementById('v-details').innerText = data.repeticoes[0].detalhe;
    }
    let html = `<div class="roll-block">
        <button class="reroll-btn" onclick="enviar('${data.comando_puro}', true)">RE-ROLAR</button>
        <div style="margin-bottom:8px">
            <strong style="color:${color}">${data.user}</strong> <span style="color:#555; font-size:0.8rem">// ${data.comentario}</span>
        </div>`;
    data.repeticoes.forEach(r => {
        let highlight = r.is_max ? 'crit-glow' : (r.is_min ? 'fail-glow' : '');
        html += `<div style="display:flex; align-items:center; gap:15px">
            <span class="total-val ${highlight}">${r.total}</span>
            <span style="color:#8b949e; font-size:0.8rem">🎲 ${r.detalhe} (d${r.lados})</span>
        </div>`;
    });
    const log = document.getElementById('log');
    log.innerHTML += html + `</div>`;
    log.scrollTop = log.scrollHeight;
});

socket.on('sync_init', function(data) {
    const list = document.getElementById('initiative-list');
    list.innerHTML = "";
    data.lista.forEach((item, idx) => {
        const active = (idx === data.turno) ? "active" : "";
        list.innerHTML += `<li class="init-item ${active}">
            <span style="color:${getPColor(item.user_origem)}; font-weight:bold">${item.entidade}</span>
            <div style="display:flex; align-items:center; gap:8px">
                <input type="number" value="${item.valor}" 
                       class="init-edit-input" 
                       onchange="updateManualInit('${item.entidade}', this.value)">
                <span style="cursor:pointer; color:#444;" onclick="socket.emit('delete_single_init',{room:room,entidade:'${item.entidade}'})">✕</span>
            </div>
        </li>`;
    });
});

function updateManualInit(entidade, novoValor) {
    socket.emit('update_init_value', {room: room, entidade: entidade, valor: novoValor});
}

socket.on('new_message', function(data) {
    document.getElementById('log').innerHTML += `<div style="padding:5px"><strong style="color:${getPColor(data.user)}">${data.user}:</strong> <span>${data.msg}</span></div>`;
    document.getElementById('log').scrollTop = document.getElementById('log').scrollHeight;
});

socket.on('status', function(data) {
    document.getElementById('log').innerHTML += `<div style="color:#484f58; text-align:center; font-size:0.75rem; margin:10px 0;">${data.msg}</div>`;
});