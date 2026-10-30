/* Scripts do site · Leonardo Santa Cecília
   1) Ano do rodapé.
   2) Medição: clique nos botões de WhatsApp, por página e por posição do botão.
      Não envia dados pessoais: só o nome da página e a posição do botão.
      - Com Google Tag Manager: o evento vai para o dataLayer como "whatsapp_click".
      - Com a Google Tag (gtag.js) direto na página: o evento é enviado por gtag('event', ...).
      Em nenhum caso há envio se não houver Tag Manager nem gtag instalados. */
(function () {
  var ano = document.getElementById('ano');
  if (ano) ano.textContent = new Date().getFullYear();

  var pagina = document.body.getAttribute('data-page') || location.pathname;

  function registrar(posicao) {
    var parametros = { wa_page: pagina, wa_position: posicao };
    if (typeof window.gtag === 'function') {
      window.gtag('event', 'whatsapp_click', parametros);
      return;
    }
    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({ event: 'whatsapp_click', wa_page: pagina, wa_position: posicao });
  }

  var links = document.querySelectorAll('a[href*="wa.me"]');
  for (var i = 0; i < links.length; i++) {
    (function (a) {
      a.addEventListener('click', function () {
        registrar(a.getAttribute('data-wa') || 'outro');
      });
    })(links[i]);
  }
})();

/* 3) Menu no celular: fecha ao escolher uma página ou ao tocar fora. */
(function () {
  var menu = document.querySelector('.menu-m');
  if (!menu) return;
  menu.addEventListener('click', function (e) { if (e.target.closest('a')) menu.removeAttribute('open'); });
  document.addEventListener('click', function (e) { if (menu.open && !menu.contains(e.target)) menu.removeAttribute('open'); });
})();
