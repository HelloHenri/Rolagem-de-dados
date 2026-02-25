import re
import random
from flask import Flask, render_template
from flask_socketio import SocketIO, join_room, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Armazena os dados das salas: {'sala_id': {'lista': [], 'turno': 0}}
salas_iniciativa = {}

def resolver_rolagem(comando, eh_reroll=False):
    padrao = re.compile(r'(?:(\d+)#)?(\d+)?d(\d+)(?:([+-]\d+))?(.*)')
    raw_cmd = comando.strip().lower()
    match = padrao.match(raw_cmd)
    
    if not match: return None

    repeticoes = int(match.group(1)) if match.group(1) else 1
    quantidade = int(match.group(2)) if match.group(2) else 1
    lados = int(match.group(3))
    bonus = int(match.group(4)) if match.group(4) else 0
    comentario_original = match.group(5).strip()

    cmd_puro = raw_cmd.split(' ')[0]
    comentario = f"Re-rolando {cmd_puro}" if eh_reroll else (comentario_original or "Ação")

    resultados_finais = []
    for _ in range(repeticoes):
        giros = [random.randint(1, lados) for _ in range(quantidade)]
        giros.sort()
        puro = sum(giros)
        resultados_finais.append({
            'detalhe': f"[{', '.join(map(str, giros))}] {f'{bonus:+}' if bonus != 0 else ''}",
            'total': puro + bonus,
            'lados': lados,
            'is_max': (puro == lados * quantidade),
            'is_min': (puro == 1 * quantidade)
        })
    
    return {'repeticoes': resultados_finais, 'comentario': comentario, 'comando_puro': cmd_puro}

@app.route('/')
def index(): return render_template('index.html')

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    emit('status', {'msg': f"⚔️ {data['username']} entrou na sessão."}, room=room)
    if room in salas_iniciativa:
        emit('sync_init', salas_iniciativa[room], room=room)

@socketio.on('send_command')
def handle_command(data):
    eh_reroll = data.get('is_reroll', False)
    res = resolver_rolagem(data['msg'], eh_reroll)
    room = data['room']
    
    if res:
        emit('new_roll', {
            'user': data['username'], 
            'comentario': res['comentario'], 
            'repeticoes': res['repeticoes'],
            'comando_puro': res['comando_puro'],
            'eh_reroll': eh_reroll
        }, room=room)
        
        if "iniciativa" in res['comentario'].lower():
            if room not in salas_iniciativa: 
                salas_iniciativa[room] = {'lista': [], 'turno': 0}
            
            lista = salas_iniciativa[room]['lista']
            val = res['repeticoes'][0]['total']
            
            regex_init = re.compile(r'iniciativa\s*(.*)', re.IGNORECASE)
            match_nome = regex_init.search(res['comentario'])
            nome_entidade = match_nome.group(1).strip() if match_nome and match_nome.group(1) else data['username']
            
            for item in lista:
                if item['entidade'].lower() == nome_entidade.lower():
                    lista.remove(item)
                    break
            
            lista.append({'entidade': nome_entidade, 'user_origem': data['username'], 'valor': val})
            lista.sort(key=lambda x: x['valor'], reverse=True)
            emit('sync_init', salas_iniciativa[room], room=room)
    else:
        emit('new_message', {'user': data['username'], 'msg': data['msg']}, room=room)

@socketio.on('update_init_value')
def update_init_value(data):
    room = data['room']
    entidade = data['entidade']
    try:
        novo_valor = int(data['valor'])
        if room in salas_iniciativa:
            lista = salas_iniciativa[room]['lista']
            for item in lista:
                if item['entidade'] == entidade:
                    item['valor'] = novo_valor
                    break
            lista.sort(key=lambda x: x['valor'], reverse=True)
            emit('sync_init', salas_iniciativa[room], room=room)
    except: pass

@socketio.on('delete_single_init')
def delete_single(data):
    room = data['room']
    entidade = data['entidade']
    if room in salas_iniciativa:
        lista = salas_iniciativa[room]['lista']
        salas_iniciativa[room]['lista'] = [i for i in lista if i['entidade'] != entidade]
        if len(salas_iniciativa[room]['lista']) > 0:
            salas_iniciativa[room]['turno'] %= len(salas_iniciativa[room]['lista'])
        else:
            salas_iniciativa[room]['turno'] = 0
        emit('sync_init', salas_iniciativa[room], room=room)

@socketio.on('next_turn')
def next_turn(data):
    room = data['room']
    if room in salas_iniciativa and len(salas_iniciativa[room]['lista']) > 0:
        salas_iniciativa[room]['turno'] = (salas_iniciativa[room]['turno'] + 1) % len(salas_iniciativa[room]['lista'])
        emit('sync_init', salas_iniciativa[room], room=room)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)