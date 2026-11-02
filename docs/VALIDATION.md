# Validação da candidata 0.9.0-beta

Ambiente de desenvolvimento: Omarchy 4.0.6 (Arch), Python 3.14, PySide6/Qt 6.12.0, plataforma Qt offscreen. Não é uma instalação limpa. Nenhum teste aplica alterações ao perfil real do desenvolvedor.

## Verificado automaticamente

- Regressões das funcionalidades originais: enquadramento, filtros, paletas, importação de imagens, presets/histórico e fluxo de aplicação.
- Perfis nativos/Flatpak fictícios: relativos, absolutos, espaços, padrão, duplicados, ausentes e INI inválido.
- XDG temporário, migração por cópia, originais e histórico preservados, recusa de dados inválidos ou destino já utilizado.
- Cores, modo sólido sem decodificação, CSS sem imagem, presets com imagem incorporada e validação de conteúdo.
- Backup/restauração dos arquivos; imports próprios sem duplicação; CSS externo e `user.js` preservados; legado identificado; recusa de links simbólicos e alterações externas; falhas de escrita/permissão simuladas.
- Interface offscreen: quatro seções, splitter empilhado/horizontal, troca de modos, contraste do popup, galeria progressiva e callbacks na thread gráfica.

Comando: `QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME= python -m unittest discover -s tests -v`.

Resultados e construção final são registrados em `docs/TEST-RESULTS.txt` e `docs/BUILD-RESULTS.md`.

As capturas `veil-solid.png` e `veil-image.png` foram produzidas no Qt offscreen. Não representam validação visual de CSS dentro do navegador. Foram inspecionados também o popup do combo e uma janela estreita.

## Transparência nativa da barra

Inspeção somente de leitura do Zen instalado, versão 1.24b (build 20261029123729): os estilos `zen-browser-ui.css` e `zen-theme.css` mostram fundos independentes na raiz, wrapper e `#zen-browser-background`, além do fundo da barra. A opção Linux `zen.widget.linux.transparency` é consumida pelo tema nativo. O Veil agora limpa essas camadas apenas no modo sólido com transparência acima de zero e remove o fundo forçado do wrapper de conteúdo. O destino Navegador inteiro pinta uma camada única em #zen-browser-background e limpa overlays nativos da barra e wrappers, sem modificar o DOM dos sites. Não aplica CSS às páginas.

Referência externa: [preferências do Transparent Zen](https://raw.githubusercontent.com/zen-browser/theme-store/main/themes/642854b5-88b4-4c40-b256-e035532109df/preferences.json), indicado pelo [guia Zen Zero](https://www.sameerasw.com/zen). A implementação do Veil não instala nem depende desse mod ou da extensão para sites.

Testes adicionais cobrem ativação explícita das duas preferências, idempotência, restauração após persistência simulada pelo Zen, retorno a imagem/opaco, reversão com CSS externo e recusa de bloco editado. A restauração pode manter um bloco de overrides com os valores originais em user.js para desfazer preferências já persistidas no navegador.

Não foi possível testar o efeito visual: `hyprctl` não consegue acessar o socket gráfico e abrir um socket de automação em loopback retorna `Operation not permitted`. A leitura do código instalado e os testes de arquivos não comprovam o resultado visual em uma janela real.

Os testes dos dois destinos cobrem seletor e prévia, enquadramento com dimensões próprias, limite do canvas sólido, persistência em presets, geração de uma única camada global, ativação/restauração de preferências ao trocar de destino e ausência da base opaca que podia produzir o contorno claro. A captura `veil-full-browser.png` foi produzida e inspecionada offscreen e representa somente o fundo; não comprova o resultado visual no navegador.

Compatibilidade com outros fundos: foi identificado no perfil selecionado o fundo `wave-light.png` ativado pelo Transparent Zen. O Veil agora inclui uma regra condicionada à preferência desse mod para neutralizar somente a imagem decorativa na raiz da janela enquanto gerencia o fundo. A aplicação de produção foi feita com backup e hashes confirmaram que os arquivos do outro mod e prefs.js não mudaram. Os testes fictícios cobrem essa preservação e a restauração. A inspeção visual após reiniciar o navegador permanece pendente.

Contraste dos controles: corrigido o escopo anteriormente restrito ao titlebar. A proteção agora cobre as variáveis de primeiro plano do navigator-toolbox, ícones nativos ativos e campo/placeholder da pesquisa, sem regras de display/visibility ou recoloração de favicons. A mudança foi aplicada ao perfil selecionado com backup; o autor confirmou a legibilidade dos controles após reiniciar o Zen. A biblioteca ainda precisou de uma correção adicional, descrita a seguir.

## Conferência final solicitada pelo autor

Em 2026-11-02, o autor confirmou a leitura dos ícones/pesquisa e, após a correção adicional, confirmou a legibilidade da biblioteca/histórico no Zen real. O painel zen-library possui paleta própria fora do navigator-toolbox; agora recebe cores claras e uma superfície escura translúcida. Esse retorno valida esses controles, não todos os layouts ou sites.

A matriz de integração executa os quatro cenários (imagem/barra, imagem/janela, sólido transparente/barra, sólido transparente/janela) pela aplicação Qt em perfis fictícios. Cada cenário aplica CSS, simula a persistência de preferências após reinício, restaura o estado anterior, reaplica, desativa, restaura a desativação e confirma os arquivos de outro mod intactos. Um teste reproduziu e eliminou uma janela de concorrência em que edições externas durante a preparação podiam ser sobrescritas: agora são verificadas também antes do snapshot.

80 testes automatizados passaram. Nenhum reinício real do navegador, nem inspeção visual completa de cada cenário, é simulado como se tivesse sido realizado. O agente continua sem acesso ao socket gráfico.

## Adiado pelo autor: ambiente limpo; demais verificações manuais

O teste em ambiente limpo foi explicitamente adiado nesta etapa, por solicitação do autor. Antes de v1.0.0, executar com usuário Linux separado ou VM Arch. Registrar versão do Zen, origem do pacote, compositor, escala e fontes. Repetir com Flatpak e ambiente sem Hyprland.

| Etapa | Resultado |
|---|---|
| Instalar dependências e pacote em Arch limpo | Pendente |
| Abrir pelo menu de aplicativos real | Pendente |
| Descobrir e selecionar perfis novos/múltiplos | Pendente em instalação real |
| Selecionar imagem e conferir enquadramento | Pendente no Zen |
| Aplicar cor sólida e paleta de abas | Pendente no Zen |
| Reiniciar Zen manualmente e inspecionar CSS | Pendente |
| Desativar/restaurar, preservando outro mod | Pendente no Zen |
| Desinstalar e verificar dados preservados | Pendente em máquina limpa |
| Wayland, X11, fontes maiores e escalas 100/150/200% | Pendente em sessões gráficas reais |
| Interromper processo durante uma transação | Pendente; há backup prévio, mas não atomicidade multifarquivo |

Não declarar a versão estável nem afirmar compatibilidade visual com uma versão específica do Zen antes de completar essas etapas.
