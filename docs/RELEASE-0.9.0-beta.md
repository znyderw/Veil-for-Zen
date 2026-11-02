# Veil for Zen v0.9.0-beta — notas da beta local

Aplicativo Linux independente para personalizar imagem, cor e transparência na barra lateral ou no fundo inteiro do Zen Browser. Não é um produto oficial do Zen. Código original sob MIT; dependências e conteúdo de terceiros mantêm suas licenças (NOTICE.md).

## O que inclui

- Interface escura com quatro seções, splitter responsivo e prévia assíncrona.
- Fundo sólido com transparência, imagem com enquadramento/filtros, paletas de abas e dois destinos de fundo.
- Detecção de perfis nativos/Flatpak, XDG e migração por cópia dos dados antigos.
- Presets portáteis, histórico de aparência e recuperação de CSS com backup.
- Compatibilidade com o fundo decorativo do Transparent Zen e cores legíveis nos controles e na biblioteca.
- Proteção contra sobrescrita de edições externas inclusive durante a preparação da transação.
- Wheel Python, fonte e pacote Arch, comando/desktop/ícone, instalação isolada e desinstalação que preserva dados.

## Artefatos locais

- `dist/veil_for_zen-0.9.0b0-py3-none-any.whl`
- `dist/veil-for-zen-0.9.0-beta.tar.gz`
- `dist/veil-for-zen-0.9.0beta-1-any.pkg.tar.zst`
- `dist/PKGBUILD` com hash real da fonte.
- `dist/SHA256SUMS`

A versão PEP 440 é 0.9.0b0. A tag anotada local prevista para o commit final é v0.9.0-beta. O script de preparação não publica nem altera tags. A confirmação do commit/tag e a identidade dos artefatos são registradas no relatório final da preparação.

## Validação e decisões

80 testes automatizados passaram, incluindo os quatro cenários de fundo, aplicação/restauração/desativação em perfis fictícios e preservação de outro mod. As capturas da interface foram atualizadas com perfil fictício e arte geométrica própria licenciada sob MIT. O autor confirmou os ícones e a biblioteca/histórico legíveis no Zen real após as correções.

O teste em ambiente limpo (VM/usuário novo) foi adiado explicitamente pelo autor. A inspeção visual completa dos quatro cenários e da restauração dentro do Zen continua pendente: o agente não tem acesso ao socket gráfico. Esses limites não são apresentados como testes concluídos.

## Limitações conhecidas

- Beta, sem declaração de estabilidade. Seletores dependem da versão do Zen; pode haver conflitos com mods não testados.
- Sites e novas abas com fundo próprio cobrem o fundo da janela; não é injetado CSS em sites.
- A prévia é aproximada. Não há medição exata do DOM nem cores por domínio/favicon.
- Não há expiração automática de backups/cache ou pacote Flatpak do Veil.
- Construção Arch local foi feita com ferramentas já disponíveis, sob as condições de BUILD-RESULTS.md.
- O histórico Git anterior à preparação contém a biblioteca antiga; não foi reescrito. A árvore atual e os artefatos excluem wallpapers particulares.

## Publicação

A release, o push da tag/commit, a alteração de visibilidade do repositório e a submissão ao AUR não foram executados automaticamente. Os artefatos e notas estão preparados para revisão. A v1.0.0 exige completar o teste em ambiente limpo e as verificações reais de instalação, CSS e recuperação.
