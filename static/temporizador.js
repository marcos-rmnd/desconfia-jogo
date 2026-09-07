const TOTAL = 15
let restando = TOTAL
const numEl  = document.getElementById('timer-num')
const barEl  = document.getElementById('timer-barra')
const form   = document.getElementById('form-golpe')
const tick = setInterval(() => { restando--
  numEl.textContent = restando
  const pct = (restando / TOTAL) * 100
  let cor = '#69ff47'
  if (restando <= 10) cor = '#ffd32a'
  if (restando <= 5)  cor = '#ff4757'

  barEl.style.width      = pct + '%'
  barEl.style.background = cor
  numEl.style.color      = cor
  if (restando <= 0) {
    clearInterval(tick)
    document.getElementById('timeout-input').value = 'true'
    form.submit()
  }
}, 1000)
form.addEventListener('submit', () => clearInterval(tick))