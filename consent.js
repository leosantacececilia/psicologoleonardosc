/* Aviso de cookies e Google Consent Mode v2 · Leonardo Santa Cecília
   Como ligar a medição: preencha GOOGLE_TAG_ID abaixo com o ID da sua Google Tag
   (formato "G-XXXXXXXXXX", do Google Analytics 4) ou do seu contêiner do Tag Manager
   (formato "GTM-XXXXXXX"). Enquanto estiver vazio, nada é carregado e o aviso não aparece.
   O que acontece:
   - Antes de qualquer carregamento, o consentimento padrão é "negado" (Consent Mode v2).
   - O aviso oferece "Aceitar" e "Recusar" com o mesmo destaque. A escolha fica no
     navegador da pessoa (localStorage, chave "lsc-consent"), sem envio a terceiros.
   - A Google Tag só é carregada depois de "Aceitar" (modo básico de consentimento).
     Se preferir o modo avançado (carregar sempre, com pings sem cookies quando recusado),
     mude CARREGAR_SEM_CONSENTIMENTO para true. Recomendação: manter false (LGPD). */
(function () {
  var GOOGLE_TAG_ID = '';
  var CARREGAR_SEM_CONSENTIMENTO = false;
  var CHAVE = 'lsc-consent';
  var raiz = (document.body && document.body.getAttribute('data-root')) || '';

  window.dataLayer = window.dataLayer || [];
  function comando() { window.dataLayer.push(arguments); }

  comando('consent', 'default', {
    ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied',
    analytics_storage: 'denied', wait_for_update: 500
  });

  function ler() { try { return localStorage.getItem(CHAVE); } catch (e) { return null; } }
  function gravar(v) { try { localStorage.setItem(CHAVE, v); } catch (e) {} }

  var carregada = false;
  function carregarTag() {
    if (carregada || !GOOGLE_TAG_ID) return;
    carregada = true;
    var s = document.createElement('script'); s.async = true;
    if (GOOGLE_TAG_ID.indexOf('GTM-') === 0) {
      window.dataLayer.push({ 'gtm.start': new Date().getTime(), event: 'gtm.js' });
      s.src = 'https://www.googletagmanager.com/gtm.js?id=' + GOOGLE_TAG_ID;
    } else {
      window.gtag = function () { window.dataLayer.push(arguments); };
      window.gtag('js', new Date());
      window.gtag('config', GOOGLE_TAG_ID, { anonymize_ip: true });
      s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GOOGLE_TAG_ID;
    }
    document.head.appendChild(s);
  }

  function aplicar(escolha) {
    if (escolha === 'granted') {
      comando('consent', 'update', { analytics_storage: 'granted' });
      carregarTag();
    } else if (CARREGAR_SEM_CONSENTIMENTO) {
      carregarTag();
    }
  }

  function montarAviso() {
    if (document.getElementById('aviso-cookies')) return;
    var div = document.createElement('div');
    div.id = 'aviso-cookies'; div.className = 'cookie-banner';
    div.setAttribute('role', 'region'); div.setAttribute('aria-label', 'Aviso de cookies');
    div.innerHTML =
      '<p>Uso cookies de estatística (Google Analytics) só para entender quais páginas ajudam mais. ' +
      'Nada do que você conversa comigo em sessão passa por aqui. ' +
      '<a href="' + raiz + 'privacidade/">Política de privacidade</a></p>' +
      '<div class="cookie-actions">' +
      '<button type="button" class="btn btn-sm" data-consent="granted">Aceitar</button>' +
      '<button type="button" class="btn btn-sm btn-navy" data-consent="denied">Recusar</button>' +
      '</div>';
    document.body.appendChild(div);
    var botoes = div.querySelectorAll('button[data-consent]');
    for (var i = 0; i < botoes.length; i++) {
      botoes[i].addEventListener('click', function () {
        var v = this.getAttribute('data-consent');
        gravar(v); aplicar(v); div.parentNode.removeChild(div);
      });
    }
  }

  function iniciar() {
    raiz = document.body.getAttribute('data-root') || raiz;
    var escolha = ler();
    if (escolha === 'granted' || escolha === 'denied') { aplicar(escolha); }
    else if (GOOGLE_TAG_ID) { montarAviso(); }
    var abrir = document.querySelectorAll('a[data-consent="abrir"]');
    for (var i = 0; i < abrir.length; i++) {
      abrir[i].addEventListener('click', function (e) {
        e.preventDefault();
        try { localStorage.removeItem(CHAVE); } catch (err) {}
        if (GOOGLE_TAG_ID) { montarAviso(); }
        else { alert('Nenhum cookie de estatística está ativo neste site no momento.'); }
      });
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar); else iniciar();
})();
