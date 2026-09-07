from urllib.parse import urlencode
GOOGLE_FORM_BASE_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfZGLWvmjEExTfbjd-SBWPEnazClI0wcIOq2EnzCL6TaTN5Ug/viewform"
GOOGLE_FORM_ENTRY_NOME = "entry.465034840"     # campo Nome
GOOGLE_FORM_ENTRY_PONTOS = "entry.648214172"   # campo Pontuação

def montar_link_forms(nome, pontos):
    params = {
        GOOGLE_FORM_ENTRY_NOME: nome,
        GOOGLE_FORM_ENTRY_PONTOS: pontos,
        'usp': 'pp_url'
    }
    return f"{GOOGLE_FORM_BASE_URL}?{urlencode(params)}"