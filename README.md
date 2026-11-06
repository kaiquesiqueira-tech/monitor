# MONITOR PC E SC ALMOXARIFADO

Acompanhamento de pedidos de compra com entrega vencida e solicitações de compra
paradas há mais de 30 dias, restrito aos itens que têm ponto de pedido cadastrado
(itens de reposição de estoque).

Roda no navegador do computador e do celular. É um site estático: não precisa de
servidor, banco de dados nem instalação.

## Arquivos

| Arquivo | Para que serve |
| --- | --- |
| `index.html` | O monitor inteiro: tela, filtros, detalhe do produto e gerador de Excel |
| `dados.js` | A base extraída do Protheus. É o único arquivo que muda a cada atualização |
| `gerar_dados.py` | Converte os três relatórios do Protheus em `dados.js` |
| `verificar.py`, `agendar.bat`, `desagendar.bat` | Verificação automática de 2 em 2 minutos, sem janela aberta |
| `sincronizar.py`, `sincronizar.bat` | Mesma coisa, porém numa janela aberta que mostra cada passo |
| `publicar.bat` | Gera e publica na hora, com um clique |
| `historico.js` | Um retrato por dia, para o gráfico de tendência |
| `resumo_do_dia.txt` | Texto pronto para colar no WhatsApp, gerado a cada publicação |
| `dados/` | Onde ficam os `.xlsx` exportados do Protheus (não vão para o GitHub) |
| `manifest.webmanifest`, `sw.js`, `icone*.png` | Fazem o site virar aplicativo instalável no celular |

## Rodando na sua máquina

Abra o `index.html` com duplo clique. Funciona direto do disco, sem servidor.

## Publicando no GitHub Pages

1. Crie um repositório no GitHub e suba esta pasta.
2. No repositório, vá em **Settings > Pages**.
3. Em *Source*, escolha **Deploy from a branch**, branch `main`, pasta `/ (root)`.
4. Em um ou dois minutos o endereço aparece na própria tela de Pages.

> **Atenção:** no plano gratuito, o GitHub Pages é sempre público, mesmo com o
> repositório privado. O `dados.js` contém preços, fornecedores, nomes de compradores
> e a posição de compras das cinco filiais. Se esses dados não podem ser públicos,
> hospede em um servidor interno da empresa, no SharePoint, ou use uma conta
> GitHub Enterprise, que permite Pages com acesso restrito.

## Funciona sem internet

O monitor guarda no aparelho a tela e a última base carregada. Abrindo sem conexão, ele
mostra tudo o que já tinha, inclusive a ficha dos produtos, os filtros, o Excel e o texto
do WhatsApp. O cabeçalho avisa "sem conexão, usando a última base baixada". Quando a
internet volta, ele busca a base nova sozinho, sem recarregar a página.

A abertura também ficou mais rápida: a tela vem do próprio aparelho e a rede é consultada
em paralelo, só para atualizar o que mudou.

## Instalando no celular

Abrindo o endereço no celular aparece o botão **Instalar** no cabeçalho. No Android ele
chama o instalador do próprio navegador; no iPhone mostra o passo a passo do Safari, que
não tem instalação automática. No computador o botão também aparece, no Chrome e no Edge.

Instalado, o monitor abre pelo ícone, em tela cheia, sem a barra do navegador, e continua
funcionando sem internet com a última base baixada. Quem já instalou não vê mais o botão.

## Atualizando a base pelo script

Alternativa para quem prefere linha de comando, ou para deixar automatizado:

1. No Protheus, exporte os três browses para Excel e salve em `dados/` com estes nomes:
   - `dados/mata110.xlsx` — solicitações de compra em aberto
   - `dados/mata121.xlsx` — pedidos de compra em aberto
   - `dados/PROD_EM_PP.xlsx` — SBZ, produtos com ponto de pedido
   - `dados/SALDO_FISICO_02.xlsx` e `dados/SALDO_FISICO_10.xlsx` — SB2, saldo em estoque
     (qualquer arquivo começando com `SALDO` é lido; são dois porque as filiais estão
     em grupos diferentes no Protheus)
   - `dados/SB1.xlsx` — cadastro de produtos, usado só para o tipo (MC, ME, EP, SV…)
   - `dados/CENTRO_DE_CUSTO.xlsx` — descrição dos centros de custo (já traz a filial)
   - `dados/CLASSE_DE_VALOR_*.xlsx` — descrição das classes de valor, uma tabela por
     empresa. Como o arquivo não diz a filial, o gerador descobre sozinho qual tabela
     pertence a cada filial pelos códigos que aparecem nos documentos, e mostra a
     relação na tela ao publicar
2. Instale as dependências uma única vez: `pip install pandas openpyxl`
3. Rode `python gerar_dados.py`
4. Faça commit e push. O site atualiza sozinho.

Os dias de atraso são recalculados toda vez que a página abre, usando a data do dia,
então o monitor continua correto entre uma atualização e outra.

## Compartilhar no WhatsApp

O botão **Enviar no WhatsApp**, ao lado do Baixar Excel, monta um resumo do que estiver
na tela: os totais e a lista dos doze itens mais críticos, cada um com número do pedido
ou da solicitação, código do produto, data de emissão e descrição.

No celular abre a caixa de compartilhamento do aparelho já com a planilha em anexo, então
o Excel vai junto com o texto. No computador vai direto para o WhatsApp Web, em
`web.whatsapp.com`, com a mensagem pronta — só falta escolher o contato ou o grupo. O anexo
não vai junto nesse caminho; para o arquivo, use o Baixar Excel.

A mensagem também é copiada para a área de transferência, então, se o navegador bloquear a
janela ou o WhatsApp Web pedir login, basta colar.

A troca de base é feita só pelo computador, com o `sincronizar.bat` ou o `publicar.bat`.

## Busca

O campo **Buscar** separa o que é número do que é texto, como a consulta de produtos
do Protheus:

- **Número** procura só em código de produto, número de pedido, número de solicitação,
  centro de custo, classe de valor, grupo e data. Com ou sem os zeros da frente:
  `020100033` e `20100033` dão o mesmo resultado, e `72449` acha o pedido 072449.
  Não casa com pedaço solto no meio de outro número nem com a descrição.
- **Palavra** procura no começo das palavras da descrição, do fornecedor, do comprador,
  do tipo, do centro de custo e da classe. `cat` acha CAT e CATRACA.
- **Referência no meio da descrição** também é encontrada. As palavras se partem na barra,
  no hífen e na vírgula, então `3/8`, `1,75` e `3945` acham AR. LISA 3/8, M12-1,75 e
  RETENTOR CAT 107-3945. E qualquer trecho de quatro letras ou mais é procurado dentro das
  palavras: `4207` acha FILTRO FLEETGUARD AF4207 e `20lt` acha PAIL 20LT.
- Várias palavras valem em qualquer ordem: `filtro cat` e `cat filtro` dão o mesmo.
- Acento não atrapalha nos dois sentidos, e quando nada bate exatamente ele tenta de novo
  aceitando um erro de digitação, avisando no rodapé que são os parecidos.

A data aceita `10/02/2026`, `02/2026` para o mês e `2026` para o ano.

## As abas

- **Pedidos de compra** — tudo em aberto, com o atraso de entrega em destaque.
- **Solicitações de compra** — o que ainda não virou pedido.
- **Reposição** — itens com saldo abaixo do ponto de pedido, mostrando se já existe
  pedido ou solicitação cobrindo a falta. É a aba que evita a parada.
- **Resumo** — rankings, evolução dia a dia e emissões por mês, filial a filial.

## Solicitante da SC

Se a exportação de solicitações tiver uma coluna com o solicitante (`Solicitante`,
`Solicitado por` ou `Cod.Solicit`), ela aparece na ficha de cada solicitação. Sem a coluna,
o campo mostra "não informado". No Protheus, é o campo `C1_SOLICIT` do browse MATA110.

## Nome do fornecedor

Se a exportação de pedidos tiver uma coluna com o nome do fornecedor (`Nome Fornecedor`,
`Razao Social` ou `Nome`), o monitor passa a mostrar o nome no lugar do código, sem
nenhum ajuste. Basta incluir a coluna no browse do Protheus.

## Como os itens são classificados

- **Com ponto de pedido na filial** — o produto tem cadastro no SBZ da mesma filial
  do pedido ou da solicitação. É o filtro padrão da tela.
- **Com ponto de pedido em qualquer filial** — o produto tem cadastro em outra filial.
  Serve para achar falha de cadastro.
- **Todos os itens** — sem filtro, incluindo compras que não são de reposição.

O monitor abre mostrando **todos** os pedidos e todas as solicitações em aberto. O seletor
**Situação** restringe para só os vencidos, vencidos há mais de 30 dias, e assim por diante.
As faixas de cor no topo separam o que está dentro do prazo do que está vencido, em blocos de
até 30 dias, 31 a 90, 91 a 180 e acima de 180 — clicar numa faixa filtra a lista.
