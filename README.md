# Site · Leonardo Santa Cecília

Site profissional publicado em **https://psicologoleonardosc.com** pelo GitHub Pages.

## Como está configurado

- **Hospedagem:** GitHub Pages, a partir da branch `main` deste repositório (grátis).
- **Domínio:** psicologoleonardosc.com, registrado na HostGator (renovação no painel da HostGator em 06/07/2027).
- **DNS (HostGator, opção "Sem hospedagem — apenas Zona de DNS"):**
  - A `@` → 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153
  - CNAME `www` → leosantacececilia.github.io

## Como atualizar o site

No GitHub, abra o `index.html`, clique no **lápis (Edit)**, altere o texto e clique em **Commit changes**. O site atualiza em cerca de 1 minuto.

- **Páginas:** `index.html` (início), `tcc-online/index.html`, `burnout-trabalho/index.html`, `ansiedade-trabalho/index.html`, `tdah-adulto/index.html`, `como-funciona/index.html` e `privacidade/index.html`. Os textos de cada página estão no arquivo dela, na ordem em que aparecem.
- **Cores e fontes:** ficam em `estilo.css`, usado por todas as páginas.
- **WhatsApp:** procure por `wa.me`. Cada página tem uma mensagem automática própria ("Vi a página sobre burnout…", "Li a página Como funciona…"), para você saber de onde veio cada contato. A da página inicial é "Vim pelo seu site…".
- **Medição (opcional):** `site.js` registra o clique nos botões de WhatsApp (evento `whatsapp_click`, com página e posição do botão, sem dados pessoais). Para ligar o Google Analytics ou o Tag Manager, preencha `GOOGLE_TAG_ID` em `consent.js`; o aviso de cookies só aparece depois disso, e a tag só carrega depois do "Aceitar".
- **Privacidade:** a política está em `privacidade/index.html`. Se incluir uma ferramenta nova no site, atualize a política e a data no fim dela.
- **Search Console:** o `sitemap.xml` lista as páginas públicas. Se escolher a verificação por meta tag, cole a tag no `index.html`, na linha indicada logo abaixo do `canonical`.
- **Fotos:** envie um arquivo novo com o mesmo nome (`leonardo-retrato-880.jpg`, `leonardo-sobre.jpg` etc.) em **Add file → Upload files**.

## Cuidados éticos (CFP) já aplicados

- Nome profissional e CRP visíveis no topo, junto à foto e no rodapé
- Sem preço usado como propaganda (os valores são passados pelo WhatsApp)
- Sem depoimentos de pacientes e sem promessa de resultado
- Aviso de que o site não é serviço de emergência (sem números de crise; urgência e emergência são combinadas no primeiro contato, conforme a Res. CFP 09/2024)
- Sem nome, avaliações ou selos da Zenklub (se a Zenklub confirmar por escrito que pode, dá para incluir)
