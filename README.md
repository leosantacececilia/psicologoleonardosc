# Site · Leonardo Santa Cecília (versão identidade nova)

Site profissional pronto para publicar no **GitHub Pages** com o domínio **psicologoleonardosc.com**.

## O que tem nesta pasta

| Arquivo | Para que serve |
|---|---|
| `index.html` | O site inteiro (textos, layout, links) |
| `assets/` | Fotos, logo em vetor, fontes, favicon e imagem de compartilhamento |
| `CNAME` | Diz ao GitHub qual é o seu domínio |
| `404.html` | Página que aparece se alguém digitar um endereço errado |
| `robots.txt`, `sitemap.xml` | Ajudam o Google a encontrar o site |

---

## Parte 1 · Subir no GitHub (uns 10 minutos)

1. Entre em **github.com** e crie uma conta (se ainda não tiver). Anote seu nome de usuário.
2. No canto superior direito, clique em **+ → New repository**.
   - *Repository name*: `psicologoleonardosc` (pode ser outro nome)
   - Marque **Public**
   - Clique em **Create repository**
3. Na página que abrir, clique no link **uploading an existing file**.
4. Descompacte o zip no seu computador, abra a pasta `site-leonardo-v2` e **arraste todo o conteúdo dela** (o `index.html`, a pasta `assets`, o `CNAME` etc.) para a área de upload. Arraste o conteúdo, não a pasta.
5. Clique em **Commit changes**.
   > Confira: o `index.html` precisa aparecer direto na lista principal do repositório, e não dentro de outra pasta.
6. Vá em **Settings → Pages**.
   - Em *Build and deployment → Source*, escolha **Deploy from a branch**
   - Em *Branch*, escolha **main** e **/(root)** → **Save**
7. Ainda em **Settings → Pages**, o campo **Custom domain** deve mostrar `psicologoleonardosc.com` (o arquivo `CNAME` preenche sozinho). Se estiver vazio, digite o domínio e clique em **Save**.

> Até a Parte 2 ficar pronta, o GitHub vai mostrar um aviso de DNS. É normal.

---

## Parte 2 · Apontar o domínio (HostGator)

Seu domínio está registrado até **06/08/2027** e o DNS dele está na **HostGator** (servidores `ns1070.hostgator.com.br` e `ns1071.hostgator.com.br`). A configuração é feita lá.

**Onde editar:**
- **Se você ainda tem plano de hospedagem na HostGator:** entre no **cPanel → Editor de Zona** (*Zone Editor*) → `psicologoleonardosc.com` → **Gerenciar**.
- **Se não tem mais hospedagem:** procure a opção de DNS do domínio no **Portal do Cliente HostGator**. Se não encontrar, abra um chamado no suporte e peça: *"Quero apontar meu domínio para o GitHub Pages e preciso editar os registros A e CNAME."*

**O que configurar:**

1. **Apague** os registros **A** antigos de `psicologoleonardosc.com` (os que apontam para um IP da HostGator) e o registro antigo de `www`.
2. **Crie** estes registros:

| Tipo | Nome | Valor |
|---|---|---|
| A | `@` (ou `psicologoleonardosc.com`) | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `SEU-USUARIO.github.io` |

Troque `SEU-USUARIO` pelo seu nome de usuário do GitHub. Não mexa em registros **MX** ou **TXT** que já existirem.

A mudança costuma valer em minutos, mas pode levar até 24–48 horas.

---

## Parte 3 · Cadeado de segurança (HTTPS)

Quando o domínio já estiver abrindo, volte em **Settings → Pages** e marque **Enforce HTTPS**. Essa opção pode levar até 24 horas para ficar disponível.

**Recomendado:** o GitHub sugere verificar o domínio na sua conta (**foto de perfil → Settings → Pages → Add a domain**). Ele pede para criar um registro TXT na HostGator. Isso impede que outra pessoa use o seu domínio no GitHub.

---

## Alternativa: se você ainda paga hospedagem na HostGator

Nesse caso, você nem precisa do GitHub: no **cPanel → Gerenciador de Arquivos → public_html**, envie todo o conteúdo desta pasta (menos `CNAME` e `README.md`) e pronto. Se preferir o GitHub (gratuito), dá para cancelar a hospedagem depois que o site estiver no ar por lá.

---

## Como atualizar o site depois

No GitHub, abra o `index.html`, clique no **lápis (Edit)**, altere o texto e clique em **Commit changes**. O site atualiza em cerca de 1 minuto.

- **WhatsApp e mensagem automática:** procure por `wa.me` no `index.html` (aparece 6 vezes).
- **Textos:** estão todos no `index.html`, na ordem em que aparecem na página.
- **Fotos:** substitua os arquivos em `assets/` mantendo os mesmos nomes.

## Cuidados éticos (CFP) já aplicados

- Nome profissional e CRP visíveis no topo, junto à foto e no rodapé
- Sem preço usado como propaganda (os valores são passados pelo WhatsApp)
- Sem depoimentos de pacientes e sem promessa de resultado
- Aviso de que o site não é serviço de emergência, com CVV (188) e SAMU (192)
- Sem nome, avaliações ou selos da Zenklub (as regras da plataforma para uso da marca fora dela não são públicas; se a Zenklub confirmar por escrito que pode, dá para incluir)
