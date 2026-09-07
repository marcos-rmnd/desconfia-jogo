// MENU DE FECHAR JANELA
function abrirModalFechar() {
  document.getElementById('modal-fechar').style.display = 'flex';
}
function fecharModal() {
  document.getElementById('modal-fechar').style.display = 'none';
}
function fecharPagina() {
  window.close();
  // fallback, em caso de o navegador bloquear window.close() (aba não aberta via script)
  document.getElementById('modal-fechar').innerHTML = '<div class="modal-caixa"><p>Pode fechar essa aba com segurança</p></div>';
}

// ESCONDE O BOTÃO DO FORMS DEPOIS DE CLICADO/ABERTO
function abrirForms(link) {
  window.open(link, '_blank');
  document.getElementById('btn-forms').style.display = 'none';
  localStorage.setItem('forms_enviado', 'true');
}
document.addEventListener('DOMContentLoaded', function() {
  if (localStorage.getItem('forms_enviado') === 'true') {
    const btn = document.getElementById('btn-forms');
    if (btn) btn.style.display = 'none';
  }
});