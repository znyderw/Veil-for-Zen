# Auditoria e implementação — Veil for Zen 0.9.0-beta

## Base auditada

O Studio 2.0 tinha 28 testes, separação entre `core/` e `ui/`, geometria CSS, filtros em QImage, extração determinística de paletas, QThreadPool para prévia/importação/biblioteca, QSplitter, presets/histórico e aplicação com backup. PySide6 é a única dependência de execução.

Problemas encontrados: perfil pessoal fixo, configurações e biblioteca no diretório de instalação, nenhuma descoberta de perfis, inexistência de restauração/desativação pública, ausência de pacote/comando, prévia sem ampliação proporcional acima de 100%, biblioteca inteira carregada de uma vez e popups sem cores explícitas. O CSS utiliza seletores internos do Zen e não fornece coloração por domínio/favicon; essa limitação foi preservada de forma explícita.

## Arquivos e responsabilidades

| Arquivo/grupo | Mudança |
|---|---|
| `veil_for_zen/__main__.py`, `__init__.py` | Nome, versão beta, inicialização, identidade Qt e oferta de migração |
| `studio.py` | Lançador compatível com instalações antigas |
| `veil_for_zen/core/paths.py` | Configuração/dados/cache XDG |
| `veil_for_zen/core/profiles.py` | INI, caminhos nativos/Flatpak, seleção e permissões |
| `veil_for_zen/core/migration.py` | Cópia das imagens/JSON antigos; originais preservados |
| `veil_for_zen/core/settings.py` | Campos de fundo sólido, validação e persistência fora da instalação |
| `veil_for_zen/core/presets.py` | CRUD preservado, exportação/importação portáteis |
| `veil_for_zen/core/zen_integration.py`, `chrome.css` | CSS próprio, cópia de imagem, locks, snapshots, hashes, rollback, desativação e restauração |
| `veil_for_zen/core/rendering.py`, `image_library.py` | Cache de renderização, modo sólido sem imagem, miniaturas e lotes |
| `veil_for_zen/core/color_extractor.py` | Algoritmo existente preservado sob o pacote novo |
| `veil_for_zen/ui/theme.py` | Fusion, QPalette explícita e QSS centralizado para controles/popups |
| `veil_for_zen/ui/controls_panel.py` | Quatro seções, seleção de modo, seletor/hex/recentes, controles relevantes |
| `veil_for_zen/ui/main_window.py` | Perfil visível, splitter responsivo, biblioteca progressiva, presets/histórico separados na interface e ações de recuperação |
| `veil_for_zen/ui/preview.py` | Renderização assíncrona preservada; cache invalidado por metadados da imagem e ampliação proporcional |
| `veil_for_zen/assets/veil-for-zen.svg` | Ícone vetorial próprio, sem marca oficial do Zen |
| `pyproject.toml`, `requirements.txt` | Pacote e comando `veil-for-zen`, requisitos de Python/Qt |
| `packaging/` | Desktop e receita Arch |
| `tools/` | Build, artefatos/checksums, instalação/remoção e benchmark |
| `tests/test_studio.py`, `tests/test_public.py` | Regressões originais adaptadas e testes de distribuição pública |
| `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `docs/` | Uso público, migração, manutenção, relatórios e pendências |
| `.gitignore` | Caches, dados pessoais e artefatos de build excluídos |

`core/`, `ui/` e `chrome.css` foram movidos para um pacote Python instalável. Nenhuma funcionalidade foi substituída por simulação. A classe antiga `Studio` permanece como alias de compatibilidade de `VeilWindow`. Prefixos CSS internos `--zss-*` foram mantidos para reduzir alterações no motor existente; os arquivos/imports e dados novos usam `veil-for-zen`.

## Resultado por fase

1. Auditoria/estabilização: concluídas no código e regressões automatizadas.
2. Interface: implementada e inspecionada offscreen; sessões reais Wayland/X11 pendentes.
3. Funcionalidades: cor sólida com transparência, dois destinos de fundo (barra/janela inteira), controles de abas e presets portáteis implementados.
4. Performance: caches/lotes implementados; amostras antes/depois em PERFORMANCE.md. Filtros inéditos não ficaram mais rápidos nesta amostra.
5. Compatibilidade: perfis, XDG, migração e CSS seguros testados com dados fictícios.
6. Distribuição: wheel/receita/pacote Arch construídos; fluxo de instalação/remoção exercitado offline sob as condições de BUILD-RESULTS.md.
7. Testes/documentação: 80 testes automatizados passaram. Validação em ambiente limpo adiada explicitamente pelo autor.
8. Release candidata: artefatos e notas preparados localmente; licença MIT aplicada, commit/tag locais preparados e publicação pendente.

Os testes usam apenas perfis fictícios e XDG temporários. Na correção posterior solicitada para a imagem decorativa do Transparent Zen, o CSS de compatibilidade foi aplicado ao perfil selecionado por meio da transação normal do Veil, com backup. Os arquivos e preferências do outro mod, as configurações antigas e a biblioteca pessoal foram preservados. Não houve publicação no GitHub/AUR, criação de release remota. A licença MIT foi escolhida com autorização do autor. A candidata não é declarada estável.
