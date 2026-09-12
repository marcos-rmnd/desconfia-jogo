from flask import Flask, render_template, redirect, url_for, request, session
from forms_helper import montar_link_forms
from flask_session import Session
import json
import os
import random
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'Desconfia!-br-2026') #para acesso remoto e local
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
GAME_KEYS = {'QUIZ': 'quiz', 'GOLPE OU NAO?': 'golpe', 'E AGORA?': 'agora'}

#ACESSO À BASE DE DADOS
basedir = os.path.abspath(os.path.dirname(__file__))
# Se houver DATABASE_URL definida no ambiente (Render), usa ela. Se não, usa SQLite local.
db_url = os.environ.get('DATABASE_URL')
if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'scores.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True, 'pool_recycle': 300,
}
db = SQLAlchemy(app)

# CONFIGURAÇÃO DE SESSÃO NO BANCO DE DADOS (Neon)
app.config['SESSION_TYPE'] = 'sqlalchemy'
app.config['SESSION_SQLALCHEMY'] = db
app.config['SESSION_PERMANENT'] = False
Session(app)

# MODELO DA TABELA A USAR
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    pontos = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    data = db.Column(db.DateTime, default=datetime.now)
# Cria a tabela no arquivo
with app.app_context():
    db.create_all()

#FUNÇÕES E CONFIGURAÇÕES GERAIS DOS JOGOS
def carregar(arquivo):
    caminho = os.path.join(os.path.dirname(__file__), arquivo)
    with open(caminho, encoding='utf-8') as f:
        return json.load(f)

def init_sessao():
    if 'pontos' not in session:
        session['pontos'] = 0
        session['acertos'] = 0
        session['total'] = 0

def acertou():
    session['pontos'] = session.get('pontos', 0) + 10
    session['acertos'] = session.get('acertos', 0) + 1
    session['total'] = session.get('total', 0) + 1
    session['ac_jogo'] = session.get('ac_jogo', 0) + 1
    session['tot_jogo'] = session.get('tot_jogo', 0) + 1
    session['pts_jogo'] = session.get('pts_jogo', 0) + 10
    session.modified = True

def errou():
    session['vidas'] = session.get('vidas', 3) - 1
    session['total'] = session.get('total', 0) + 1
    session['tot_jogo'] = session.get('tot_jogo', 0) + 1
    session.modified = True

def marcar_jogo_como_concluido():
    chave = GAME_KEYS.get(session.get('jogo', ''))
    if chave:
        jogos = session.get('jogos_completos', {})
        jogos[chave] = True
        session['jogos_completos'] = jogos
        session.modified = True

def classificar(ac, tot):
    if tot == 0:
        return {'label': '?', 'cls': 'cls-atento', 'pct': 0, 'desc': 'Nenhuma questão respondida ainda...ou só está de brincadeira.'}
    pct = round(ac / tot * 100)
    if pct <= 40:
        return {'label': 'ISCA', 'cls': 'cls-isca', 'pct': pct,
                'desc': 'Provavelmente você clicaria em "Parabéns, você foi selecionado(a)!"'}
    if pct <= 70:
        return {'label': 'ATENTO', 'cls': 'cls-atento', 'pct': pct,
                'desc': 'Você desconfia em algumas situações, mas ainda pode cair em um golpe bem feito!'}
    if pct <= 90:
        return {'label': 'BLINDADO', 'cls': 'cls-blindado', 'pct': pct,
                'desc': 'O golpista provavelmente vai perder tempo tentando'}
    return {'label': 'PERITO', 'cls': 'cls-Perito', 'pct': pct, 'desc': 'Você já pode até dar aulas no grupo da família!'}

def salvar_pontuacao(nome, pontos, total):
    try:
        score_id = session.get('score_id')
        if score_id:
            registro = Score.query.get(score_id)
            if registro:
                registro.pontos = pontos
                registro.total = total
                registro.data = datetime.now()
                db.session.commit()
                return
        novo_score = Score(nome=nome, pontos=pontos, total=total)
        db.session.add(novo_score)
        db.session.commit()
        session['score_id'] = novo_score.id
        session.modified = True
    except Exception as e:
        db.session.rollback()
        print(f"ERRO ao salvar pontuação: {e}")

@app.route('/')
def menu():
    init_sessao()
    if 'nome_jogador' not in session:
        return redirect(url_for('login'))
    jogos = session.get('jogos_completos', {'quiz': False, 'golpe': False, 'agora': False})
    todos_completos = all(jogos.values())
    link_forms = None
    if todos_completos:
        link_forms = montar_link_forms(session.get('nome_jogador', ''), session.get('pontos', 0))
    return render_template('menu.html',
            pontos=session.get('pontos', 0),
            acertos=session.get('acertos', 0),
            total=session.get('total', 0),
            jogos=jogos,
            todos_completos = todos_completos,
            link_forms = link_forms
        )

#JOGO 1 - HORA DO QUIZ
@app.route('/quiz/iniciar')
def quiz_iniciar():
    if session.get('jogos_completos', {}).get('quiz'):
        return redirect(url_for('menu'))
    init_sessao()
    perguntas = carregar('quiz.json')
    perguntas = [p for p in perguntas if 'alternativas' in p]
    fila = random.sample(perguntas, min(15, len(perguntas)))
    session['fila'] = fila
    session['idx'] = 0
    session['vidas'] = 3
    session['ac_jogo'] = 0
    session['tot_jogo'] = 0
    session['pts_jogo'] = 0
    session['jogo'] = 'QUIZ'
    session.modified = True
    return redirect(url_for('quiz_pergunta'))
@app.route('/quiz/pergunta')
def quiz_pergunta():
    if session.get('jogos_completos', {}).get('quiz') and not session.get('fila'):
        return redirect(url_for('menu'))
    fila = session.get('fila', [])
    idx = session.get('idx', 0)
    print(f"DEBUG: Estamos no quiz. Índice atual: {idx}, Tamanho da fila: {len(fila)}")
    vidas = session.get('vidas', 3)
    if vidas <= 0:
        marcar_jogo_como_concluido()
        return redirect(url_for('game_over'))
    if idx >= len(fila):
        marcar_jogo_como_concluido()
        return redirect(url_for('resultados'))
    q = fila[idx]
    num = idx + 1
    tot = len(fila)
    return render_template('quiz.html',
            q=q, num=num, tot=tot,
            pct=round(num / tot * 100),
            vidas=vidas,
            pontos=session.get('pontos', 0)
            )
@app.route('/quiz/responder', methods=['POST'])
def quiz_responder():
    fila = session.get('fila', [])
    idx = session.get('idx', 0)
    q = fila[idx]
    escolha = request.form.get('resposta', '')
    certa = escolha == q['correta']
    if certa:
        acertou()
    else:
        errou()
    session['idx'] = idx + 1
    session.modified = True
    vidas = session.get('vidas', 3)
    fim_de_jogo = (idx + 1 >= len(fila)) or (vidas <= 0)
    if fim_de_jogo:
        marcar_jogo_como_concluido()
    return render_template('avaliacao.html',
            certa=certa,
            escolha=escolha,
            correta=q['correta'],
            explicacao=q['explicacao'],
            proximo_url=url_for('quiz_pergunta'),
            vidas=vidas,
            pontos=session.get('pontos', 0),
            idx=idx + 1,
            tot=len(fila),
            jogo='QUIZ',
            fim_de_jogo=fim_de_jogo
            )

#JOGO 2 -É GOLPE OU NÃO?
@app.route('/golpe/iniciar')
def golpe_iniciar():
    init_sessao()
    if session.get('jogos_completos', {}).get('golpe'):
        return redirect(url_for('menu'))
    mensagens = carregar('mensagens.json')
    mensagens = [m for m in mensagens if 'veredito' in m]
    random.shuffle(mensagens)
    session['fila'] = mensagens
    session['idx'] = 0
    session['vidas'] = 3
    session['ac_jogo'] = 0
    session['tot_jogo'] = 0
    session['pts_jogo'] = 0
    session['jogo'] = 'GOLPE OU NAO?'
    session.modified = True
    return redirect(url_for('golpe_mensagem'))
@app.route('/golpe/mensagem')
def golpe_mensagem():
    if session.get('jogos_completos', {}).get('golpe') and not session.get('fila'):
        return redirect(url_for('menu'))
    fila = session.get('fila', [])
    idx = session.get('idx', 0)
    vidas = session.get('vidas', 3)
    if vidas <= 0:
        marcar_jogo_como_concluido()
        return redirect(url_for('game_over'))
    if idx >= len(fila):
        marcar_jogo_como_concluido()
        return redirect(url_for('resultados'))
    m = fila[idx]
    num = idx + 1
    tot = len(fila)
    return render_template('golpe.html',
            m=m, num=num, tot=tot,
            vidas=vidas,
            pontos=session.get('pontos', 0)
        )
@app.route('/golpe/responder', methods=['POST'])
def golpe_responder():
    fila = session.get('fila', [])
    idx = session.get('idx', 0)
    m = fila[idx]
    escolha = request.form.get('resposta', '')
    timeout = request.form.get('timeout', 'false') == 'true'
    certa = (not timeout) and (escolha == m['veredito'])
    if certa:
        acertou()
    else:
        errou()
    session['idx'] = idx + 1
    session.modified = True
    vidas = session.get('vidas', 3)
    fim_de_jogo = (idx + 1 >= len(fila)) or (vidas <= 0)
    if fim_de_jogo:
        marcar_jogo_como_concluido()
    gabarito = 'GOLPE' if m['veredito'] == 'G' else 'LEGITIMO'
    return render_template('avaliacao.html',
            certa=certa,
            escolha=escolha,
            correta=gabarito,
            explicacao=m['explicacao'],
            timeout=timeout,
            proximo_url=url_for('golpe_mensagem'),
            vidas=vidas,
            pontos=session.get('pontos', 0),
            idx=idx + 1,
            tot=len(fila),
            jogo='É GOLPE OU NAO?',
            fim_de_jogo=fim_de_jogo
            )

#JOGO 3 - E AGORA? (o que fazer em cada situação)
@app.route('/agora/iniciar')
def agora_iniciar():
    if session.get('jogos_completos', {}).get('agora'):
        return redirect(url_for('menu'))
    init_sessao()
    situacoes = carregar('situacoes.json')
    situacoes = [s for s in situacoes if 'opcoes' in s]
    random.shuffle(situacoes)
    session['fila'] = situacoes
    session['idx'] = 0
    session['vidas'] = 3
    session['ac_jogo'] = 0
    session['tot_jogo'] = 0
    session['pts_jogo'] = 0
    session['jogo'] = 'E AGORA?'
    session.modified = True
    return redirect(url_for('agora_situacao'))
@app.route('/agora/situacao')
def agora_situacao():
    if session.get('jogos_completos', {}).get('agora') and not session.get('fila'):
        return redirect(url_for('menu'))
    fila = session.get('fila', [])
    idx = session.get('idx', 0)
    vidas = session.get('vidas', 3)
    if vidas <= 0:
        marcar_jogo_como_concluido()
        return redirect(url_for('game_over'))
    if idx >= len(fila):
        marcar_jogo_como_concluido()
        return redirect(url_for('resultados'))
    s = fila[idx]
    num = idx + 1
    tot = len(fila)
    return render_template('agora.html',
            s=s, num=num, tot=tot,
            pct=round(num / tot * 100),
            vidas=vidas,
            pontos=session.get('pontos', 0)
            )
@app.route('/agora/responder', methods=['POST'])
def agora_responder():
    fila = session.get('fila', [])
    idx = session.get('idx', 0)
    s = fila[idx]
    escolha = request.form.get('resposta', '')
    certa = escolha == s['correta']
    if certa:
        acertou()
    else:
        errou()
    session['idx'] = idx + 1
    session.modified = True
    vidas = session.get('vidas', 3)
    fim_de_jogo = (idx + 1 >= len(fila)) or (vidas <= 0)
    if fim_de_jogo:
        marcar_jogo_como_concluido()
    return render_template('avaliacao.html',
            certa=certa,
            escolha=escolha,
            correta=s['correta'],
            explicacao=s['explicacao'],
            proximo_url=url_for('agora_situacao'),
            vidas=vidas,
            pontos=session.get('pontos', 0),
            idx=idx + 1,
            tot=len(fila),
            jogo='E AGORA?',
            fim_de_jogo=fim_de_jogo
            )

#LOGIN - inserir um nome
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form['nome']
        session['nome_jogador'] = nome
        session['jogos_completos'] = {'quiz': False, 'golpe': False, 'agora': False}
        session.pop('score_id', None)
        session.modified = True
        return redirect(url_for('menu'))
    return render_template('login.html')

#RESULTADOS
@app.route('/resultados')
def resultados():
    nome = session.get('nome_jogador', 'Anônimo')
    pontos = session.get('pontos', 0)
    total = session.get('total', 0)
    salvar_pontuacao(nome, pontos, total)
    chave = GAME_KEYS.get(session.get('jogo', ''))
    if chave:
        jogos = session.get('jogos_completos', {})
        jogos[chave] = True
        session['jogos_completos'] = jogos
        session.modified = True
    ac = session.get('ac_jogo', 0)
    tot = session.get('tot_jogo', 0)
    cls = classificar(ac, tot)
    return render_template('resultados.html',
            jogo=session.get('jogo', ''),
            ac=ac, tot=tot,
            pts=session.get('pts_jogo', 0),
            pontos=session.get('pontos', 0),
            cls=cls,
            gameover=False,
            fim_de_jogo=True
            )
#PERDEU
@app.route('/gameover')
def game_over():
    chave = GAME_KEYS.get(session.get('jogo',''))
    if chave:
        jogos = session.get('jogos_completos',{})
        if not jogos.get(chave):
            jogos[chave] = True
            session['jogos_completos'] = jogos
            session.modified = True
    nome = session.get('nome_jogador', 'Anônimo')
    pontos = session.get('pontos', 0)
    total = session.get('total', 0)
    salvar_pontuacao(nome, pontos, total)
    ac = session.get('ac_jogo', 0)
    tot = session.get('tot_jogo', 0)
    cls = classificar(ac, tot)
    return render_template('resultados.html',
            jogo=session.get('jogo', ''),
            ac=ac, tot=tot,
            pts=session.get('pts_jogo', 0),
            pontos=session.get('pontos', 0),
            cls=cls,
            gameover=True,
            fim_de_jogo = True
        )
#PONTUAÇÃO
@app.route('/pontos')
def pontuacao():
    init_sessao()
    ac = session.get('acertos', 0)
    tot = session.get('total', 0)
    cls = classificar(ac, tot)
    return render_template('pontos.html',
            pontos=session.get('pontos', 0),
            acertos=ac,
            total=tot,
            erros=tot - ac,
            cls=cls
        )
#BOTÃO SAIR E RESET
@app.route('/resetar')
def resetar():
    session.clear()
    return redirect(url_for('login'))
#REGRAS
@app.route('/regras')
def regras():
    return render_template('regras.html')
#EXECUTADOR
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)